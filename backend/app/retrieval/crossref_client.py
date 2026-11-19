
import httpx
from urllib.parse import quote

BASE_URL = "https://api.crossref.org/works"


def get_work_by_doi(doi: str) -> dict | None:
    """Retrieve publication metadata from Crossref using a DOI."""

    if not doi or not doi.strip():
        raise ValueError("DOI cannot be empty.")

    doi = doi.strip()

    # Remove DOI URL prefixes if supplied.
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):].strip()
            break

    encoded_doi = quote(doi, safe="")
    url = f"{BASE_URL}/{encoded_doi}"

    try:
        response = httpx.get(
            url,
            timeout=20.0,
            headers={"User-Agent": "CiteVerify/0.1"}
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Crossref returned HTTP {exc.response.status_code}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Could not connect to Crossref: {exc}"
        ) from exc

    work = response.json()["message"]

    authors = [
        author.get("given", "") + " " + author.get("family", "")
        for author in work.get("author", [])
    ]

    published = work.get("published", {}).get("date-parts", [])
    year = published[0][0] if published and published[0] else None

    return {
        "title": work.get("title", [None])[0],
        "doi": work.get("DOI"),
        "authors": [author.strip() for author in authors],
        "publication_year": year,
        "publisher": work.get("publisher"),
        "type": work.get("type"),
        "url": work.get("URL"),
    }
