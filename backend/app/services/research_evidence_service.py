from __future__ import annotations

import re
from typing import Any

from ..retrieval.paper_search_service import search_academic_papers
from ..retrieval.paper_matcher import match_paper
from ..retrieval.source_downloader import download_paper
from ..retrieval.source_parser import extract_pdf_text
from ..retrieval.evidence_chunker import chunk_paper_text
from ..retrieval.evidence_retriever import retrieve_evidence
from ..retrieval.research_models import (
    ResearchEvidenceRequest,
    ResearchEvidencePreparation,
)
from ..verification.enums import RetrievalStatus
from ..verification.schemas import VerificationRequest


def _paper_identifier(paper: dict[str, Any]) -> str:
    raw = (
        paper.get("openalex_id")
        or paper.get("semantic_scholar_id")
        or paper.get("doi")
        or paper.get("title")
        or "research-paper"
    )
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw)).strip("_")
    return (safe or "research-paper")[:100]


def _empty_preparation(
    request: ResearchEvidenceRequest,
    *,
    search_status: str,
    citation_match_status: str,
    retrieval_status: RetrievalStatus,
    limitations: list[str],
    papers_found: int = 0,
) -> ResearchEvidencePreparation:
    verification_request = VerificationRequest(
        claim_id=request.claim_id,
        claim_text=request.claim_text,
        citation_ids=request.citation_ids,
        claim_type=request.claim_type,
        evidence=[],
        retrieval_status=retrieval_status,
        source_limitations=limitations,
    )
    return ResearchEvidencePreparation(
        search_status=search_status,
        citation_match_status=citation_match_status,
        papers_found=papers_found,
        papers_processed=0,
        evidence_count=0,
        retrieval_status=retrieval_status,
        source_limitations=limitations,
        papers=[],
        verification_request=verification_request,
    )


def prepare_research_evidence(
    request: ResearchEvidenceRequest,
) -> ResearchEvidencePreparation:
    """Search, match, download, parse, chunk and rank evidence for a claim.

    The returned VerificationRequest is shaped for Member 3's existing
    /api/v1/verification/run endpoint. No claim verdict is generated here.
    """
    query = (
        request.search_query
        or request.citation_title
        or request.citation_doi
        or ""
    ).strip()
    if not query:
        raise ValueError("A research search query or citation is required.")

    search_result = search_academic_papers(
        query=query,
        per_page=request.per_page,
        doi=request.citation_doi,
    )
    papers: list[dict[str, Any]] = search_result.get("papers", [])
    limitations: list[str] = []

    source_status = search_result.get("source_status", {})
    for source_name, info in source_status.items():
        if info.get("status") == "UNAVAILABLE":
            limitations.append(
                f"{source_name} search was unavailable: {info.get('error', 'unknown error')}"
            )

    citation_was_supplied = bool(request.citation_title or request.citation_doi)
    citation_match_status = "NOT_REQUESTED"

    if citation_was_supplied:
        match = match_paper(
            {
                "title": request.citation_title or "",
                "doi": request.citation_doi or "",
                "authors": request.citation_authors,
                "publication_year": request.publication_year,
            },
            papers,
        )
        citation_match_status = match["status"]
        if match["status"] == "RESOLVED":
            selected_papers = [match["matched_paper"]]
        elif match["status"] == "AMBIGUOUS":
            limitations.append(match.get("reason", "Citation match is ambiguous."))
            return _empty_preparation(
                request,
                search_status=search_result.get("status", "UNKNOWN"),
                citation_match_status=citation_match_status,
                retrieval_status=RetrievalStatus.AMBIGUOUS,
                limitations=limitations,
                papers_found=len(papers),
            )
        else:
            limitations.append(match.get("reason", "No matching cited paper was found."))
            return _empty_preparation(
                request,
                search_status=search_result.get("status", "UNKNOWN"),
                citation_match_status=citation_match_status,
                retrieval_status=RetrievalStatus.NOT_FOUND,
                limitations=limitations,
                papers_found=len(papers),
            )
    else:
        # Topic-search results are candidates, not confirmed citation matches.
        selected_papers = papers[:request.max_papers]
        limitations.append(
            "Papers were selected by topical search. The exact cited reference was not supplied or identity-matched."
        )

    if not selected_papers:
        limitations.append("No research papers were returned by the available search providers.")
        return _empty_preparation(
            request,
            search_status=search_result.get("status", "UNKNOWN"),
            citation_match_status=citation_match_status,
            retrieval_status=RetrievalStatus.NOT_FOUND,
            limitations=limitations,
            papers_found=0,
        )

    all_chunks: list[dict[str, Any]] = []
    paper_summaries: list[dict[str, Any]] = []
    processed_papers = 0

    for paper in selected_papers:
        paper_id = _paper_identifier(paper)
        title = paper.get("title") or "Untitled research paper"
        source_id = str(paper.get("doi") or paper.get("openalex_id") or paper.get("semantic_scholar_id") or paper_id)
        pdf_status = "NO_PDF_URL"
        pdf_reason = "No open-access PDF URL was supplied by the search provider."
        extracted_full_text = False

        pdf_url = paper.get("pdf_url")
        if pdf_url:
            download = download_paper(str(pdf_url), paper_id)
            pdf_status = download.get("status", "UNAVAILABLE")
            pdf_reason = download.get("reason", "PDF download did not complete.")
            if download.get("status") == "FULL TEXT AVAILABLE" and download.get("file_path"):
                parsed = extract_pdf_text(download["file_path"])
                if parsed.get("status") == "SUCCESS":
                    page_chunks = chunk_paper_text(
                        parsed.get("pages", []),
                        paper_id=paper_id,
                    )
                    for chunk in page_chunks:
                        all_chunks.append({
                            **chunk,
                            "source_id": source_id,
                            "source_title": title,
                            "evidence_kind": "full_text",
                        })
                    extracted_full_text = bool(page_chunks)
                    if not extracted_full_text:
                        pdf_reason = "PDF was parsed but produced no usable text chunks."
                else:
                    pdf_reason = parsed.get("reason", "PDF text extraction failed.")

        if not extracted_full_text:
            abstract = paper.get("abstract")
            if isinstance(abstract, str) and abstract.strip():
                abstract_chunks = chunk_paper_text(
                    [{"page_number": 1, "text": abstract.strip()}],
                    paper_id=paper_id + "_abstract",
                    chunk_size=150,
                    overlap=20,
                )
                for chunk in abstract_chunks:
                    all_chunks.append({
                        **chunk,
                        "source_id": source_id,
                        "source_title": title,
                        "evidence_kind": "abstract",
                    })
                limitations.append(
                    f"Only the abstract was available for '{title}'; full-text evidence was not extracted."
                )
            else:
                limitations.append(f"No usable full text or abstract was available for '{title}': {pdf_reason}")

        paper_summaries.append({
            "title": title,
            "doi": paper.get("doi"),
            "publication_year": paper.get("publication_year"),
            "matched_sources": paper.get("sources", []),
            "pdf_status": pdf_status,
            "full_text_extracted": extracted_full_text,
            "abstract_available": bool(paper.get("abstract")),
        })
        processed_papers += 1

    ranked_chunks: list[dict[str, Any]] = []
    if all_chunks:
        ranked_chunks = retrieve_evidence(
            query=request.claim_text,
            chunks=all_chunks,
            top_k=request.top_k,
        )

    evidence: list[dict[str, Any]] = []
    for chunk in ranked_chunks:
        is_abstract = chunk.get("evidence_kind") == "abstract"
        evidence.append({
            "evidence_id": str(chunk["chunk_id"]),
            "source_id": str(chunk["source_id"]),
            "source_title": chunk["source_title"],
            "text": chunk["text"],
            # Abstracts do not have page numbers in the source paper.
            "page_number": None if is_abstract else chunk.get("page_number"),
            "section_name": "Abstract" if is_abstract else None,
            "source_type": "abstract" if is_abstract else "full_text",
            "retrieval_score": float(chunk["retrieval_score"]),
        })

    if any(item["source_type"] == "full_text" for item in evidence):
        retrieval_status = RetrievalStatus.FULL_TEXT_AVAILABLE
    elif any(item["source_type"] == "abstract" for item in evidence):
        retrieval_status = RetrievalStatus.RESOLVED
    elif selected_papers:
        retrieval_status = RetrievalStatus.METADATA_ONLY
        # Metadata-only evidence is explicit and is never sent to Gemini.
        for paper in selected_papers:
            paper_id = _paper_identifier(paper)
            evidence.append({
                "evidence_id": f"{paper_id}_metadata",
                "source_id": str(paper.get("doi") or paper.get("openalex_id") or paper.get("semantic_scholar_id") or paper_id),
                "source_title": paper.get("title"),
                "text": "",
                "page_number": None,
                "section_name": None,
                "source_type": "metadata_only",
                "retrieval_score": None,
            })
        limitations.append(
            "Publication metadata was found, but no claim-relevant full-text or abstract passage was retrieved."
        )
    else:
        retrieval_status = RetrievalStatus.NOT_FOUND

    verification_request = VerificationRequest(
        claim_id=request.claim_id,
        claim_text=request.claim_text,
        citation_ids=request.citation_ids,
        claim_type=request.claim_type,
        evidence=evidence,
        retrieval_status=retrieval_status,
        source_limitations=list(dict.fromkeys(limitations)),
    )

    return ResearchEvidencePreparation(
        search_status=search_result.get("status", "UNKNOWN"),
        citation_match_status=citation_match_status,
        papers_found=len(papers),
        papers_processed=processed_papers,
        evidence_count=sum(1 for item in evidence if item["source_type"] in {"full_text", "abstract"}),
        retrieval_status=retrieval_status,
        source_limitations=list(dict.fromkeys(limitations)),
        papers=paper_summaries,
        verification_request=verification_request,
    )
