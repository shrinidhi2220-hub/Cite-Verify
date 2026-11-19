
import re

from .openalex_client import search_works
from .semantic_scholar_client import search_papers
from .crossref_client import get_work_by_doi


def normalize_doi(doi: str) -> str:
    """Normalize DOI values before comparison."""

    if not doi:
        return ""

    doi = doi.strip().lower()

    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:"
    ):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
            break

    return doi.strip().rstrip("/")


def normalize_title(title: str) -> str:
    """Normalize paper titles for duplicate detection."""

    if not title:
        return ""

    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", " ", title)
    title = re.sub(r"\s+", " ", title)

    return title.strip()


def is_same_paper(first: dict, second: dict) -> bool:
    """Check whether two records describe the same paper."""

    first_doi = normalize_doi(first.get("doi", ""))
    second_doi = normalize_doi(second.get("doi", ""))

    # DOI takes priority when both records have one.
    if first_doi and second_doi:
        return first_doi == second_doi

    first_title = normalize_title(first.get("title", ""))
    second_title = normalize_title(second.get("title", ""))

    return bool(first_title and first_title == second_title)


def add_or_merge_paper(
    papers: list[dict],
    new_paper: dict,
    source: str
) -> None:
    """Add a paper or merge it with an existing duplicate."""

    for existing in papers:

        if is_same_paper(existing, new_paper):

            # Preserve all available author names.
            existing_authors = existing.get("authors", [])
            new_authors = new_paper.get("authors", [])

            for author in new_authors:
                if author not in existing_authors:
                    existing_authors.append(author)

            existing["authors"] = existing_authors

            # Fill fields that are currently missing.
            for key, value in new_paper.items():

                if key == "authors":
                    continue

                if value not in (None, "", [], {}):

                    if existing.get(key) in (None, "", [], {}):
                        existing[key] = value

            if source not in existing["sources"]:
                existing["sources"].append(source)

            return

    # This paper has not been encountered before.
    paper = new_paper.copy()
    paper["sources"] = [source]
    papers.append(paper)


def search_academic_papers(
    query: str,
    per_page: int = 5,
    doi: str | None = None
) -> dict:
    """
    Search OpenAlex and Semantic Scholar.

    Optionally enrich the results using Crossref DOI lookup.

    Returns unique papers and individual source statuses.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if (
        not isinstance(per_page, int)
        or isinstance(per_page, bool)
        or not 1 <= per_page <= 20
    ):
        raise ValueError("per_page must be between 1 and 20.")

    if doi is not None and (
        not isinstance(doi, str) or not doi.strip()
    ):
        raise ValueError("DOI must be a non-empty string.")

    papers = []
    source_status = {}

    # 1. Search OpenAlex
    try:
        openalex_results = search_works(
            query.strip(),
            per_page=per_page
        )

        source_status["openalex"] = {
            "status": "SUCCESS",
            "results": len(openalex_results)
        }

        for paper in openalex_results:
            add_or_merge_paper(papers, paper, "openalex")

    except RuntimeError as exc:
        source_status["openalex"] = {
            "status": "UNAVAILABLE",
            "error": str(exc)
        }

    # 2. Search Semantic Scholar
    try:
        semantic_results = search_papers(
            query.strip(),
            limit=per_page
        )

        source_status["semantic_scholar"] = {
            "status": "SUCCESS",
            "results": len(semantic_results)
        }

        for paper in semantic_results:
            add_or_merge_paper(papers, paper, "semantic_scholar")

    except RuntimeError as exc:
        source_status["semantic_scholar"] = {
            "status": "UNAVAILABLE",
            "error": str(exc)
        }

    # 3. Optional Crossref DOI lookup
    if doi:

        try:
            crossref_result = get_work_by_doi(doi)

            if crossref_result:
                source_status["crossref"] = {
                    "status": "SUCCESS"
                }

                add_or_merge_paper(
                    papers,
                    crossref_result,
                    "crossref"
                )

            else:
                source_status["crossref"] = {
                    "status": "NOT FOUND"
                }

        except RuntimeError as exc:
            source_status["crossref"] = {
                "status": "UNAVAILABLE",
                "error": str(exc)
            }

    else:
        source_status["crossref"] = {
            "status": "SKIPPED",
            "reason": "No DOI was provided."
        }

    # 4. Determine the overall retrieval status.
    has_unavailable_source = any(
        result["status"] == "UNAVAILABLE"
        for result in source_status.values()
    )

    search_sources_available = any(
        source_status[name]["status"] == "SUCCESS"
        for name in ("openalex", "semantic_scholar")
    )

    if papers:
        overall_status = (
            "PARTIAL" if has_unavailable_source else "SUCCESS"
        )

    elif search_sources_available and has_unavailable_source:
        overall_status = "INCOMPLETE"

    elif search_sources_available:
        overall_status = "NOT FOUND"

    else:
        overall_status = "UNAVAILABLE"

    return {
        "status": overall_status,
        "total_unique_papers": len(papers),
        "papers": papers,
        "source_status": source_status
    }
