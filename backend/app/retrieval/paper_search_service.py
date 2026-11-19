import re

from .openalex_client import search_works
from .semantic_scholar_client import search_papers
from .crossref_client import (
    get_work_by_doi as get_crossref_work_by_doi,
    search_works as search_crossref_works,
)
from .datacite_client import get_work_by_doi as get_datacite_work_by_doi
from .arxiv_client import get_paper_by_arxiv_doi


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
        "doi:",
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

    if first_doi and second_doi:
        return first_doi == second_doi

    first_title = normalize_title(first.get("title", ""))
    second_title = normalize_title(second.get("title", ""))

    return bool(first_title and first_title == second_title)


def add_or_merge_paper(papers: list[dict], new_paper: dict, source: str) -> None:
    """Add a paper or merge it with an existing duplicate."""
    for existing in papers:
        if is_same_paper(existing, new_paper):
            existing_authors = existing.get("authors", [])
            for author in new_paper.get("authors", []):
                if author not in existing_authors:
                    existing_authors.append(author)
            existing["authors"] = existing_authors

            for key, value in new_paper.items():
                if key == "authors":
                    continue
                if value not in (None, "", [], {}):
                    if existing.get(key) in (None, "", [], {}):
                        existing[key] = value

            if source not in existing["sources"]:
                existing["sources"].append(source)
            return

    paper = new_paper.copy()
    paper["sources"] = [source]
    papers.append(paper)


def _arxiv_doi_is_resolved(doi: str) -> dict | None:
    """Exact resolver for arXiv-issued DataCite DOIs."""
    if not doi:
        return None
    return get_paper_by_arxiv_doi(doi)


def search_academic_papers(
    query: str,
    per_page: int = 5,
    doi: str | None = None,
) -> dict:
    """
    Search academic sources and resolve DOI registries appropriately.

    Exact arXiv-issued DOIs are resolved directly through the arXiv API.
    Other DOIs are checked against Crossref, then DataCite.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if not isinstance(per_page, int) or isinstance(per_page, bool) or not 1 <= per_page <= 20:
        raise ValueError("per_page must be between 1 and 20.")

    if doi is not None and (not isinstance(doi, str) or not doi.strip()):
        raise ValueError("DOI must be a non-empty string.")

    # arXiv DOIs (10.48550/arXiv.<id>) are registered through DataCite.
    # Resolve them by their underlying arXiv ID so a Crossref 404 or
    # Semantic Scholar rate limit cannot incorrectly mark the paper absent.
    if doi:
        try:
            arxiv_paper = _arxiv_doi_is_resolved(doi)
        except RuntimeError as exc:
            arxiv_error = str(exc)
        else:
            arxiv_error = None

        if arxiv_paper:
            return {
                "status": "SUCCESS",
                "total_unique_papers": 1,
                "papers": [dict(arxiv_paper, sources=["arxiv"])],
                "source_status": {
                    "arxiv": {"status": "SUCCESS", "results": 1},
                    "openalex": {
                        "status": "SKIPPED",
                        "reason": "The exact arXiv DOI was resolved directly.",
                    },
                    "semantic_scholar": {
                        "status": "SKIPPED",
                        "reason": "The exact arXiv DOI was resolved directly.",
                    },
                    "crossref": {
                        "status": "SKIPPED",
                        "reason": "This arXiv-issued DOI is not resolved through Crossref.",
                    },
                },
            }

        # An arXiv network problem should not block the other registries.
        # Preserve the diagnostic and continue with the general search.
    else:
        arxiv_error = None

    papers: list[dict] = []
    source_status: dict = {}

    if arxiv_error:
        source_status["arxiv"] = {
            "status": "UNAVAILABLE",
            "error": arxiv_error,
        }

    try:
        openalex_results = search_works(query.strip(), per_page=per_page)
        source_status["openalex"] = {
            "status": "SUCCESS",
            "results": len(openalex_results),
        }
        for paper in openalex_results:
            add_or_merge_paper(papers, paper, "openalex")
    except RuntimeError as exc:
        source_status["openalex"] = {"status": "UNAVAILABLE", "error": str(exc)}

    try:
        semantic_results = search_papers(query.strip(), limit=per_page)
        source_status["semantic_scholar"] = {
            "status": "SUCCESS",
            "results": len(semantic_results),
        }
        for paper in semantic_results:
            add_or_merge_paper(papers, paper, "semantic_scholar")
    except RuntimeError as exc:
        source_status["semantic_scholar"] = {
            "status": "UNAVAILABLE",
            "error": str(exc),
        }

    # When the PDF bibliography has a title but no DOI, search Crossref's
    # bibliographic index. The caller still performs a strict title match;
    # these records are candidates, not automatically trusted identities.
    if not doi:
        try:
            crossref_results = search_crossref_works(query.strip(), rows=per_page)
            source_status["crossref_search"] = {
                "status": "SUCCESS",
                "results": len(crossref_results),
            }
            for paper in crossref_results:
                add_or_merge_paper(papers, paper, "crossref_search")
        except RuntimeError as exc:
            source_status["crossref_search"] = {
                "status": "UNAVAILABLE",
                "error": str(exc),
            }

    if doi:
        try:
            crossref_result = get_crossref_work_by_doi(doi)
            if crossref_result:
                source_status["crossref"] = {"status": "SUCCESS"}
                add_or_merge_paper(papers, crossref_result, "crossref")
            else:
                source_status["crossref"] = {"status": "NOT FOUND"}

                # DOI registration is distributed across agencies. A DOI
                # absent from Crossref may still be registered with DataCite.
                datacite_result = get_datacite_work_by_doi(doi)
                if datacite_result:
                    source_status["datacite"] = {"status": "SUCCESS"}
                    add_or_merge_paper(papers, datacite_result, "datacite")
                else:
                    source_status["datacite"] = {"status": "NOT FOUND"}
        except RuntimeError as exc:
            source_status["crossref"] = {
                "status": "UNAVAILABLE",
                "error": str(exc),
            }
            try:
                datacite_result = get_datacite_work_by_doi(doi)
                if datacite_result:
                    source_status["datacite"] = {"status": "SUCCESS"}
                    add_or_merge_paper(papers, datacite_result, "datacite")
                else:
                    source_status["datacite"] = {"status": "NOT FOUND"}
            except RuntimeError as datacite_exc:
                source_status["datacite"] = {
                    "status": "UNAVAILABLE",
                    "error": str(datacite_exc),
                }
    else:
        source_status["crossref"] = {
            "status": "SKIPPED",
            "reason": "No DOI was provided.",
        }
        source_status["datacite"] = {
            "status": "SKIPPED",
            "reason": "No DOI was provided.",
        }

    has_unavailable_source = any(
        result["status"] == "UNAVAILABLE"
        for result in source_status.values()
    )
    search_sources_available = any(
        source_status.get(name, {}).get("status") == "SUCCESS"
        for name in ("openalex", "semantic_scholar", "crossref_search")
    )

    if papers:
        overall_status = "PARTIAL" if has_unavailable_source else "SUCCESS"
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
        "source_status": source_status,
    }
