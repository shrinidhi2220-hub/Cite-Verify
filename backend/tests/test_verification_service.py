
import pytest

from backend.app.verification.enums import (
    Verdict,
    SourceType,
    RetrievalStatus,
    EvidenceRelation,
    VerificationMethod,
)

from backend.app.verification.schemas import (
    VerificationRequest,
    EvidencePassage,
    EvidenceAssessment,
    AIReasoningResponse,
)

import backend.app.services.verification_service as service


def make_request():

    return VerificationRequest(
        claim_id="claim_final_001",
        claim_text="The model achieved 95% accuracy.",

        retrieval_status=RetrievalStatus.FULL_TEXT_AVAILABLE,

        evidence=[
            EvidencePassage(
                evidence_id="ev_final_001",
                source_id="paper_001",
                text="The model achieved 82% accuracy.",
                page_number=5,
                source_type=SourceType.FULL_TEXT,
            )
        ],
    )


def test_complete_pipeline_with_contradicting_evidence(monkeypatch):

    def fake_gemini(request):
        return AIReasoningResponse(
            assessments=[
                EvidenceAssessment(
                    evidence_id="ev_final_001",
                    relation=EvidenceRelation.CONTRADICTS,
                    rationale="The paper reports 82%, not 95%.",
                )
            ],
            overall_notes="The reported accuracy differs.",
            limitations=[],
        )

    monkeypatch.setattr(
        service,
        "assess_with_gemini",
        fake_gemini,
    )

    result = service.verify_claim_end_to_end(make_request())

    assert result.verdict == Verdict.CONTRADICTED
    assert result.method == VerificationMethod.LLM_ASSISTED
    assert len(result.numerical_discrepancies) == 1
    assert result.human_review_required is True


def test_numerical_mismatch_prevents_simple_supported_verdict(
    monkeypatch,
):

    def fake_gemini(request):
        return AIReasoningResponse(
            assessments=[
                EvidenceAssessment(
                    evidence_id="ev_final_001",
                    relation=EvidenceRelation.SUPPORTS,
                    rationale="The evidence appears relevant.",
                )
            ],
            overall_notes="Numerical review is needed.",
            limitations=[],
        )

    monkeypatch.setattr(
        service,
        "assess_with_gemini",
        fake_gemini,
    )

    result = service.verify_claim_end_to_end(make_request())

    assert result.verdict == Verdict.PARTIALLY_SUPPORTED
    assert len(result.numerical_discrepancies) == 1


def test_insufficient_evidence_does_not_call_gemini(monkeypatch):

    def should_not_run(request):
        raise AssertionError(
            "Gemini should not run without usable evidence."
        )

    monkeypatch.setattr(
        service,
        "assess_with_gemini",
        should_not_run,
    )

    request = VerificationRequest(
        claim_id="claim_empty",
        claim_text="Treatment X is effective.",
        evidence=[],
        retrieval_status=RetrievalStatus.NOT_FOUND,
    )

    result = service.verify_claim_end_to_end(request)

    assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE
