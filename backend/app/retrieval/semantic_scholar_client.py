
import os
import httpx

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search_papers(query: str, limit: int = 5) -> list[dict]:
    """
    Search Semantic Scholar for academic papers.

    Returns paper metadata, including DOI, authors, year,
    abstract, URL and open-access PDF information.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20.")

    params = {
        "query": query.strip(),
        "limit": limit,
        "fields": "title,authors,year,externalIds,abstract,url,openAccessPdf",
    }

    headers = {
        "User-Agent": "CiteVerify/0.1"
    }

    # API key is optional.
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    try:
        response = httpx.get(
            BASE_URL,
            params=params,
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code

        if status == 429:
            raise RuntimeError(
                "Semantic Scholar rate limit reached. Try again later."
            ) from exc

        raise RuntimeError(
            f"Semantic Scholar returned HTTP {status}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not connect to Semantic Scholar: {exc}"
        ) from exc

    data = response.json()
    papers = []

    for paper in data.get("data", []):

        authors = [
            author.get("name")
            for author in paper.get("authors", [])
            if author.get("name")
        ]

        external_ids = paper.get("externalIds") or {}
        open_access_pdf = paper.get("openAccessPdf") or {}

        papers.append({
            "semantic_scholar_id": paper.get("paperId"),
            "title": paper.get("title"),
            "doi": external_ids.get("DOI"),
            "publication_year": paper.get("year"),
            "authors": authors,
            "abstract": paper.get("abstract"),
            "url": paper.get("url"),

            # New PDF information
            "pdf_url": open_access_pdf.get("url"),
            "open_access_pdf_status": open_access_pdf.get("status"),
        })

    return papers
