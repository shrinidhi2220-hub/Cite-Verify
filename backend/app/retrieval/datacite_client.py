"""Minimal DataCite DOI metadata client."""

from __future__ import annotations

from urllib.parse import quote

import httpx

BASE_URL = "https://api.datacite.org/dois"


def get_work_by_doi(doi: str) -> dict | None:
    """Retrieve metadata from DataCite. Return None when its DOI is absent."""
    if not isinstance(doi, str) or not doi.strip():
        raise ValueError("DOI cannot be empty.")

    doi = doi.strip()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):].strip()
            break

    try:
        response = httpx.get(
            f"{BASE_URL}/{quote(doi, safe='')}",
            timeout=20.0,
            headers={"User-Agent": "CiteVerify/1.0"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"DataCite returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Could not connect to DataCite: {exc}") from exc

    attributes = (response.json().get("data") or {}).get("attributes") or {}
    titles = attributes.get("titles") or []
    title = next(
        (item.get("title") for item in titles if item.get("title")),
        None,
    )

    authors = []
    for creator in attributes.get("creators") or []:
        name = creator.get("name")
        if not name:
            name = " ".join(
                part for part in (
                    creator.get("givenName"),
                    creator.get("familyName"),
                ) if part
            ).strip()
        if name:
            authors.append(name)

    abstract = next(
        (
            description.get("description")
            for description in attributes.get("descriptions") or []
            if str(description.get("descriptionType", "")).lower() == "abstract"
            and description.get("description")
        ),
        None,
    )

    return {
        "title": title,
        "doi": attributes.get("doi") or doi,
        "publication_year": attributes.get("publicationYear"),
        "authors": authors,
        "abstract": abstract,
        "url": attributes.get("url"),
        "publisher": attributes.get("publisher"),
        "type": attributes.get("types", {}).get("resourceTypeGeneral"),
    }
