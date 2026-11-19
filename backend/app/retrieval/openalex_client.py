import os
import httpx

BASE_URL = "https://api.openalex.org/works"


def search_works(query: str, per_page: int = 5) -> list[dict]:
    """Search OpenAlex and return metadata plus an available OA PDF URL."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")
    if not 1 <= per_page <= 25:
        raise ValueError("per_page must be between 1 and 25.")

    params = {
        "search": query.strip(),
        "per_page": per_page,
        # best_oa_location contains the most useful open-access location.
        "select": "id,title,doi,publication_year,authorships,best_oa_location,primary_location,open_access",
    }
    api_key = os.getenv("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key

    try:
        response = httpx.get(
            BASE_URL,
            params=params,
            timeout=20.0,
            headers={"User-Agent": "CiteVerify/1.0"},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"OpenAlex returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Could not connect to OpenAlex: {exc}") from exc

    papers = []
    for work in response.json().get("results", []):
        authors = [
            item.get("author", {}).get("display_name")
            for item in work.get("authorships", [])
            if item.get("author", {}).get("display_name")
        ]
        best_location = work.get("best_oa_location") or {}
        primary_location = work.get("primary_location") or {}
        pdf_url = (
            best_location.get("pdf_url")
            or primary_location.get("pdf_url")
        )
        papers.append({
            "openalex_id": work.get("id"),
            "title": work.get("title"),
            "doi": work.get("doi"),
            "publication_year": work.get("publication_year"),
            "authors": authors,
            "pdf_url": pdf_url,
            "open_access": (work.get("open_access") or {}).get("is_oa"),
        })
    return papers
