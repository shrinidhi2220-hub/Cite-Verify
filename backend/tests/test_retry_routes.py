from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import verification_routes
from backend.app.retrieval.research_models import ResearchEvidencePreparation
from backend.app.verification.ai_reasoner import GeminiAssessmentError
from backend.app.verification.enums import RetrievalStatus, Verdict
from backend.app.verification.schemas import VerificationRequest, VerdictDecision


client = TestClient(app)


def test_failed_gemini_job_can_retry_without_repeating_research(monkeypatch, tmp_path):
    monkeypatch.setattr(verification_routes, "JOB_STORE_PATH", tmp_path / "jobs.json")
    monkeypatch.setattr(verification_routes, "_jobs", {})

    prepared_request = VerificationRequest(
        claim_id="claim_retry_001",
        claim_text="The Transformer architecture relies on attention mechanisms.",
        citation_ids=["[1]"],
        evidence=[
            {
                "evidence_id": "transformer_page_1_chunk_1",
                "source_id": "10.48550/arXiv.1706.03762",
                "source_title": "Attention Is All You Need",
                "text": "The Transformer is based solely on attention mechanisms.",
                "page_number": 1,
                "source_type": "full_text",
                "retrieval_score": 1.25,
            }
        ],
        retrieval_status=RetrievalStatus.FULL_TEXT_AVAILABLE,
    )
    prepared = ResearchEvidencePreparation(
        search_status="SUCCESS",
        citation_match_status="RESOLVED",
        papers_found=1,
        papers_processed=1,
        evidence_count=1,
        retrieval_status=RetrievalStatus.FULL_TEXT_AVAILABLE,
        source_limitations=[],
        papers=[{
            "title": "Attention Is All You Need",
            "doi": "10.48550/arXiv.1706.03762",
            "publication_year": 2017,
            "matched_sources": ["arxiv"],
            "pdf_status": "FULL TEXT AVAILABLE",
            "full_text_extracted": True,
            "abstract_available": True,
        }],
        verification_request=prepared_request,
    )

    retrieval_calls = {"count": 0}
    verification_calls = {"count": 0}

    def fake_prepare(_request):
        retrieval_calls["count"] += 1
        return prepared

    def fake_verify(_request):
        verification_calls["count"] += 1
        if verification_calls["count"] == 1:
            raise GeminiAssessmentError(
                "Gemini request failed with INTERNAL.",
                error_code="INTERNAL",
                retryable=True,
            )
        return VerdictDecision(
            claim_id="claim_retry_001",
            verdict=Verdict.SUPPORTED,
            explanation="The retrieved passage supports the claim.",
        )

    monkeypatch.setattr(verification_routes, "prepare_research_evidence", fake_prepare)
    monkeypatch.setattr(verification_routes, "verify_claim_end_to_end", fake_verify)

    started = client.post(
        "/api/v1/verification/run-from-research",
        json={
            "claim_id": "claim_retry_001",
            "claim_text": "The Transformer architecture relies on attention mechanisms.",
            "citation_doi": "10.48550/arXiv.1706.03762",
        },
    )
    assert started.status_code == 202
    original_job_id = started.json()["job_id"]

    original_status = client.get(f"/api/v1/verification/status/{original_job_id}")
    assert original_status.status_code == 200
    original = original_status.json()
    assert original["status"] == "failed"
    assert original["retry_available"] is True
    assert original["research_summary"]["evidence_count"] == 1
    assert "Transformer is based solely" in original["research_summary"]["evidence"][0]["text"]

    retry = client.post(f"/api/v1/verification/retry/{original_job_id}")
    assert retry.status_code == 202
    retry_job_id = retry.json()["job_id"]
    assert retry_job_id != original_job_id

    retry_status = client.get(f"/api/v1/verification/status/{retry_job_id}")
    assert retry_status.status_code == 200
    completed = retry_status.json()
    assert completed["status"] == "completed"
    assert completed["result"]["verdict"] == "SUPPORTED"
    assert completed["retry_of_job_id"] == original_job_id
    assert completed["research_summary"]["evidence_count"] == 1

    # Retrieval ran once; the retry reused the original serialized request.
    assert retrieval_calls["count"] == 1
    assert verification_calls["count"] == 2

    # The job record, including the prepared request, is also written to disk.
    assert (tmp_path / "jobs.json").is_file()
