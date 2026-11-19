
import re
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_doi(doi: str) -> str:
    """Remove DOI URL prefixes and normalize DOI."""
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

    return doi.strip()


def title_similarity(title1: str, title2: str) -> float:
    """Calculate title similarity between 0 and 1."""
    first = normalize_text(title1)
    second = normalize_text(title2)

    if not first or not second:
        return 0.0

    return SequenceMatcher(None, first, second).ratio()


def match_paper(citation: dict, papers: list[dict]) -> dict:
    """
    Match a citation against retrieved academic papers.

    DOI is checked first. If unavailable, title similarity,
    author and publication year are used.
    """

    if not isinstance(citation, dict):
        raise ValueError("Citation must be a dictionary.")

    if not isinstance(papers, list):
        raise ValueError("Papers must be provided as a list.")

    if not papers:
        return {
            "status": "NOT FOUND",
            "matched_paper": None,
            "confidence": 0.0,
            "reason": "No papers were retrieved."
        }

    citation_doi = normalize_doi(citation.get("doi", ""))

    # 1. Exact DOI match
    if citation_doi:
        for paper in papers:
            paper_doi = normalize_doi(paper.get("doi", ""))

            if paper_doi and citation_doi == paper_doi:
                return {
                    "status": "RESOLVED",
                    "matched_paper": paper,
                    "confidence": 1.0,
                    "reason": "Exact DOI match."
                }

        # Do not accept a different paper when its DOI conflicts.
        if any(normalize_doi(paper.get("doi", "")) for paper in papers):
            return {
                "status": "NOT FOUND",
                "matched_paper": None,
                "confidence": 0.0,
                "reason": "No retrieved paper has the citation DOI."
            }

    # 2. Title-based matching
    citation_title = citation.get("title", "")

    if not citation_title.strip():
        return {
            "status": "NOT FOUND",
            "matched_paper": None,
            "confidence": 0.0,
            "reason": "Citation has neither a matching DOI nor a title."
        }

    scored_papers = []

    citation_authors = {
        normalize_text(author)
        for author in citation.get("authors", [])
    }

    citation_year = citation.get("publication_year")

    for paper in papers:
        similarity = title_similarity(
            citation_title,
            paper.get("title", "")
        )

        score = similarity

        paper_authors = {
            normalize_text(author)
            for author in paper.get("authors", [])
        }

        if citation_authors and paper_authors:
            if citation_authors.intersection(paper_authors):
                score += 0.05

        paper_year = paper.get("publication_year")

        if citation_year and paper_year:
            if citation_year == paper_year:
                score += 0.05

        score = min(score, 1.0)

        scored_papers.append((score, paper))

    scored_papers.sort(key=lambda item: item[0], reverse=True)

    best_score, best_paper = scored_papers[0]

    # Require a sufficiently strong match.
    if best_score < 0.85:
        return {
            "status": "NOT FOUND",
            "matched_paper": None,
            "confidence": round(best_score, 3),
            "reason": "No sufficiently strong paper match found."
        }

    # Avoid silently choosing between similarly ranked papers.
    if (
        len(scored_papers) > 1
        and best_score - scored_papers[1][0] < 0.03
    ):
        return {
            "status": "AMBIGUOUS",
            "matched_paper": None,
            "confidence": round(best_score, 3),
            "reason": "Multiple papers have similar matching scores."
        }

    return {
        "status": "RESOLVED",
        "matched_paper": best_paper,
        "confidence": round(best_score, 3),
        "reason":"Matched using title similarity and available metadata."
    }
