
import re

from backend.app.retrieval.paper_search_service import search_academic_papers
from backend.app.retrieval.source_downloader import download_paper
from backend.app.retrieval.source_parser import extract_pdf_text
from backend.app.retrieval.evidence_chunker import chunk_paper_text
from backend.app.retrieval.evidence_retriever import retrieve_evidence


def create_paper_id(paper: dict, index: int) -> str:
    """Create a stable, filesystem-safe paper ID."""

    identity = (
        paper.get("openalex_id")
        or paper.get("semantic_scholar_id")
        or paper.get("doi")
        or paper.get("title")
        or f"paper_{index}"
    )

    identity = str(identity).rstrip("/").rsplit("/", 1)[-1]

    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", identity)

    return safe_id or f"paper_{index}"


def retrieve_claim_evidence(
    query: str,
    per_page: int = 5,
    top_k: int = 5,
    doi: str | None = None
) -> dict:
    """
    Complete Member 2 research retrieval pipeline.

    1. Search academic databases.
    2. Identify accessible PDF sources.
    3. Download PDFs.
    4. Extract page-wise text.
    5. Divide text into evidence chunks.
    6. Rank evidence using BM25.

    Returns source metadata and traceable evidence passages.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty.")

    if (
        not isinstance(per_page, int)
        or isinstance(per_page, bool)
        or not 1 <= per_page <= 20
    ):
        raise ValueError("per_page must be between 1 and 20.")

    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        raise ValueError("top_k must be a positive integer.")

    # Step 1: Search academic databases.
    search_result = search_academic_papers(
        query=query,
        per_page=per_page,
        doi=doi
    )

    papers = search_result.get("papers", [])

    if not papers:
        return {
            "status": search_result["status"],
            "query": query,
            "source_status": search_result.get("source_status", {}),
            "papers_processed": [],
            "total_chunks": 0,
            "retrieved_evidence_count": 0,
            "retrieved_evidence": []
        }

    all_chunks = []
    papers_processed = []

    # Step 2: Process each retrieved paper.
    for index, paper in enumerate(papers, start=1):

        paper_id = create_paper_id(paper, index)

        source_ids = {
            "doi": paper.get("doi"),
            "openalex_id": paper.get("openalex_id"),
            "semantic_scholar_id": paper.get("semantic_scholar_id")
        }

        source_id = (
            paper.get("doi")
            or paper.get("openalex_id")
            or paper.get("semantic_scholar_id")
        )

        pdf_url = paper.get("pdf_url")

        paper_info = {
            "paper_id": paper_id,
            "source_id": source_id,
            "source_ids": source_ids,
            "title": paper.get("title"),
            "doi": paper.get("doi"),
            "publication_year": paper.get("publication_year"),
            "authors": paper.get("authors", []),
            "source_names": paper.get("sources", []),
            "pdf_url": pdf_url,
            "open_access_pdf_status": paper.get(
                "open_access_pdf_status"
            ),
            "source_url": (
                paper.get("landing_page_url")
                or paper.get("url")
                or pdf_url
            )
        }

        # Skip papers without an accessible PDF URL.
        if not pdf_url:
            papers_processed.append({
                **paper_info,
                "status": "METADATA ONLY",
                "reason": "No direct PDF URL available."
            })
            continue

        # Step 3: Download the PDF.
        download_result = download_paper(
            pdf_url=pdf_url,
            paper_id=paper_id
        )

        if download_result["status"] != "FULL TEXT AVAILABLE":
            papers_processed.append({
                **paper_info,
                "status": "DOWNLOAD UNAVAILABLE",
                "reason": download_result["reason"]
            })
            continue

        # Step 4: Extract text with original page numbers.
        parse_result = extract_pdf_text(
            download_result["file_path"]
        )

        if parse_result["status"] != "SUCCESS":
            papers_processed.append({
                **paper_info,
                "status": parse_result["status"],
                "reason": parse_result.get("reason")
            })
            continue

        # Step 5: Divide extracted text into chunks.
        chunks = chunk_paper_text(
            pages=parse_result["pages"],
            paper_id=paper_id
        )

        # Attach source metadata to every evidence chunk.
        for chunk in chunks:
            chunk.update({
                "source_id": source_id,
                "source_ids": source_ids,
                "title": paper.get("title"),
                "source_url": paper_info["source_url"],
                "pdf_url": pdf_url
            })

        all_chunks.extend(chunks)

        papers_processed.append({
            **paper_info,
            "status": "FULL TEXT AVAILABLE",
            "total_pages": parse_result.get("total_pages"),
            "extracted_pages": parse_result.get("extracted_pages"),
            "total_chunks": len(chunks)
        })

    # Step 6: Retrieve the most relevant evidence.
    evidence = retrieve_evidence(
        query=query,
        chunks=all_chunks,
        top_k=top_k
    )

    failed_papers = any(
        paper["status"] != "FULL TEXT AVAILABLE"
        for paper in papers_processed
    )

    search_was_partial = (
        search_result.get("status") == "PARTIAL"
    )

    if evidence:
        overall_status = (
            "PARTIAL"
            if failed_papers or search_was_partial
            else "SUCCESS"
        )

    elif not all_chunks:
        overall_status = "NO_RETRIEVABLE_FULL_TEXT"

    else:
        overall_status = "NO_RELEVANT_EVIDENCE"

    return {
        "status": overall_status,
        "query": query,
        "source_status": search_result.get("source_status", {}),
        "papers_processed": papers_processed,
        "total_chunks": len(all_chunks),
        "retrieved_evidence_count": len(evidence),
        "retrieved_evidence": evidence
    }
