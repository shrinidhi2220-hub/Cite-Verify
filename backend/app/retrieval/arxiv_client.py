"""Resolve arXiv-issued DOIs directly through the arXiv Atom API.

arXiv-issued DOIs use the 10.48550/arXiv.<arXiv-id> pattern. They are
registered through DataCite, not Crossref, so a Crossref-only DOI lookup
cannot resolve them reliably.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}

_ARXIV_DOI_PATTERN = re.compile(
    r"^10\.48550/arxiv\.(\d{4}\.\d{4,5})(?:v\d+)?$",
    flags=re.IGNORECASE,
)


def extract_arxiv_id_from_doi(doi: str) -> str | None:
    """Return the arXiv identifier from an arXiv-issued DOI."""
    if not isinstance(doi, str) or not doi.strip():
        return None

    normalized = doi.strip()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if normalized.lower().startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break

    match = _ARXIV_DOI_PATTERN.fullmatch(normalized)
    return match.group(1) if match else None


def get_paper_by_arxiv_id(arxiv_id: str) -> dict | None:
    """Retrieve title, authors, abstract and PDF URL for an arXiv ID."""
    if not isinstance(arxiv_id, str) or not re.fullmatch(
        r"\d{4}\.\d{4,5}", arxiv_id.strip()
    ):
        raise ValueError("A valid modern arXiv ID is required.")

    arxiv_id = arxiv_id.strip()
    try:
        response = httpx.get(
            ARXIV_API_URL,
            params={"id_list": arxiv_id},
            timeout=25.0,
            headers={"User-Agent": "CiteVerify/1.0 (academic reference resolver)"},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"arXiv returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Could not connect to arXiv: {exc}") from exc

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        raise RuntimeError("arXiv returned an unreadable Atom response.") from exc

    entry = root.find("atom:entry", ATOM_NAMESPACE)
    if entry is None:
        return None

    title = " ".join(
        (entry.findtext("atom:title", default="", namespaces=ATOM_NAMESPACE)).split()
    )
    abstract = " ".join(
        (entry.findtext("atom:summary", default="", namespaces=ATOM_NAMESPACE)).split()
    )
    entry_url = entry.findtext("atom:id", default="", namespaces=ATOM_NAMESPACE)

    authors = [
        " ".join((node.findtext("atom:name", default="", namespaces=ATOM_NAMESPACE)).split())
        for node in entry.findall("atom:author", ATOM_NAMESPACE)
    ]
    authors = [author for author in authors if author]

    published = entry.findtext(
        "atom:published", default="", namespaces=ATOM_NAMESPACE
    )
    publication_year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None

    # Preserve the exact arXiv identifier and use the canonical arXiv PDF URL.
    return {
        "arxiv_id": arxiv_id,
        "title": title or None,
        "doi": f"10.48550/arXiv.{arxiv_id}",
        "publication_year": publication_year,
        "authors": authors,
        "abstract": abstract or None,
        "url": entry_url or f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
        "open_access_status": "OPEN_ACCESS",
    }


def get_paper_by_arxiv_doi(doi: str) -> dict | None:
    """Resolve an arXiv-issued DOI by extracting and querying its arXiv ID."""
    arxiv_id = extract_arxiv_id_from_doi(doi)
    if not arxiv_id:
        return None
    return get_paper_by_arxiv_id(arxiv_id)
