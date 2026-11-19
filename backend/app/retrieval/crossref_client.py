
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


def search_works(query: str, rows: int = 5) -> list[dict]:
    """Search Crossref by a bibliography entry or paper title.

    Results are candidates only. The caller must still compare the returned
    title/authors/year with the extracted reference before accepting a DOI.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Crossref search query cannot be empty.")
    if not 1 <= rows <= 20:
        raise ValueError("Crossref rows must be between 1 and 20.")

    try:
        response = httpx.get(
            BASE_URL,
            params={"query.bibliographic": query.strip(), "rows": rows},
            timeout=12.0,
            headers={"User-Agent": "CiteVerify/1.0 (bibliographic DOI discovery)"},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Crossref search returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Could not connect to Crossref search: {exc}") from exc

    items = response.json().get("message", {}).get("items", [])
    papers: list[dict] = []
    for work in items:
        title_values = work.get("title") or []
        title = title_values[0] if title_values else None
        if not title or not work.get("DOI"):
            continue

        authors = []
        for author in work.get("author") or []:
            name = " ".join(
                part for part in (author.get("given"), author.get("family")) if part
            ).strip()
            if name:
                authors.append(name)

        date_parts = (
            work.get("published-print", {}).get("date-parts")
            or work.get("published-online", {}).get("date-parts")
            or work.get("published", {}).get("date-parts")
            or work.get("created", {}).get("date-parts")
            or []
        )
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        links = work.get("link") or []
        pdf_url = next(
            (
                item.get("URL")
                for item in links
                if "pdf" in str(item.get("content-type", "")).lower()
                and item.get("URL")
            ),
            None,
        )

        papers.append({
            "title": title,
            "doi": work.get("DOI"),
            "publication_year": year,
            "authors": authors,
            "publisher": work.get("publisher"),
            "type": work.get("type"),
            "url": work.get("URL"),
            "pdf_url": pdf_url,
        })

    return papers
