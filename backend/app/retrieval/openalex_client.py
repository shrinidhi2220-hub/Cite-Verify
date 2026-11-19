
import os
import httpx

BASE_URL = "https://api.openalex.org/works"


def search_works(query: str, per_page: int = 5) -> list[dict]:
    """
    Search OpenAlex for academic papers.

    Returns basic publication metadata for each result.
    """

    if not query.strip():
        raise ValueError("Search query cannot be empty.")

    if not 1 <= per_page <= 25:
        raise ValueError("per_page must be between 1 and 25.")

    params = {
        "search": query,
        "per_page": per_page,
        "select": "id,title,doi,publication_year,authorships",
    }

    # An API key is optional for basic testing.
    api_key = os.getenv("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key

    try:
        response = httpx.get(
            BASE_URL,
            params=params,
            timeout=20.0,
            headers={"User-Agent": "CiteVerify/0.1"},
        )
        response.raise_for_status()

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"OpenAlex returned HTTP {exc.response.status_code}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not connect to OpenAlex: {exc}"
        ) from exc

    data = response.json()
    papers = []

    for work in data.get("results", []):
        authors = [
            item.get("author", {}).get("display_name")
            for item in work.get("authorships", [])
            if item.get("author", {}).get("display_name")
        ]

        papers.append({
            "openalex_id": work.get("id"),
            "title": work.get("title"),
            "doi": work.get("doi"),
            "publication_year": work.get("publication_year"),
            "authors": authors,
        })

    return papers
