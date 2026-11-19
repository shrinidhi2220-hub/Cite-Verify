
import pytest

from backend.app.verification.enums import (
    Verdict,
    SourceType,
    RetrievalStatus,
    EvidenceRelation,
)

from backend.app.verification.schemas import (
    VerificationRequest,
    EvidencePassage,
    EvidenceAssessment,
    NumericalDiscrepancy,
)

from backend.app.verification.verdict_engine import decide_verdict


def make_request():
    return VerificationRequest(
        claim_id="claim_101",
        claim_text="The model achieved 95% accuracy.",
        retrieval_status=RetrievalStatus.FULL_TEXT_AVAILABLE,
        evidence=[
            EvidencePassage(
                evidence_id="ev_101",
                source_id="paper_101",
                text="The model achieved 95% accuracy.",
                page_number=5,
                source_type=SourceType.FULL_TEXT,
            ),
            EvidencePassage(
                evidence_id="ev_102",
                source_id="paper_101",
                text="The model achieved 90% accuracy.",
                page_number=6,
                source_type=SourceType.FULL_TEXT,
            ),
        ],
    )


def test_supported_verdict():

    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_101",
                relation=EvidenceRelation.SUPPORTS,
                rationale="The passage directly supports the claim.",
            )
        ],
    )

    assert result.verdict == Verdict.SUPPORTED
    assert "ev_101" in result.supporting_evidence_ids


def test_contradicted_verdict():

    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_102",
                relation=EvidenceRelation.CONTRADICTS,
                rationale="The reported value conflicts with the claim.",
            )
        ],
    )

    assert result.verdict == Verdict.CONTRADICTED
    assert "ev_102" in result.contradicting_evidence_ids


def test_mixed_evidence_produces_partial_verdict():

    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_101",
                relation=EvidenceRelation.SUPPORTS,
                rationale="This passage supports the claim.",
            ),
            EvidenceAssessment(
                evidence_id="ev_102",
                relation=EvidenceRelation.CONTRADICTS,
                rationale="This passage gives a conflicting result.",
            ),
        ],
    )

    assert result.verdict == Verdict.PARTIALLY_SUPPORTED
    assert result.human_review_required is True


def test_numerical_mismatch_downgrades_supported_verdict():

    discrepancy = NumericalDiscrepancy(
        claim_value="95.0",
        evidence_value="90.0",
        unit="%",
        description="The reported accuracy values differ.",
    )

    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_101",
                relation=EvidenceRelation.SUPPORTS,
                rationale="The evidence supports the main statement.",
            )
        ],
        numerical_discrepancies=[discrepancy],
    )

    assert result.verdict == Verdict.PARTIALLY_SUPPORTED
    assert len(result.numerical_discrepancies) == 1


def test_unestablished_claim_is_unsupported():

    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_101",
                relation=EvidenceRelation.DOES_NOT_ESTABLISH,
                rationale="The passage does not establish the claim.",
            )
        ],
    )

    assert result.verdict == Verdict.UNSUPPORTED


def test_unknown_evidence_id_is_rejected():

    with pytest.raises(ValueError):
        decide_verdict(
            make_request(),
            [
                EvidenceAssessment(
                    evidence_id="ev_unknown",
                    relation=EvidenceRelation.SUPPORTS,
                    rationale="Unknown evidence must not be accepted.",
                )
            ],
        )


def test_no_assessment_returns_insufficient():

    result = decide_verdict(
        make_request(),
        [],
    )

    assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE
    assert result.human_review_required is True
