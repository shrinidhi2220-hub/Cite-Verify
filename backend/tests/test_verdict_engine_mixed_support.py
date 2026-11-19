"""Regression tests for direct support mixed with partial support."""

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
)
from backend.app.verification.verdict_engine import decide_verdict


def make_request():
    return VerificationRequest(
        claim_id="claim_mixed_001",
        claim_text=(
            "The Transformer architecture relies entirely on attention "
            "mechanisms and dispenses with recurrence and convolutions."
        ),
        retrieval_status=RetrievalStatus.FULL_TEXT_AVAILABLE,
        evidence=[
            EvidencePassage(
                evidence_id="ev_101",
                source_id="paper_001",
                source_title="Attention Is All You Need",
                text=(
                    "We propose a new simple network architecture, the "
                    "Transformer, based solely on attention mechanisms, "
                    "dispensing with recurrence and convolutions entirely."
                ),
                page_number=1,
                source_type=SourceType.FULL_TEXT,
            ),
            EvidencePassage(
                evidence_id="ev_102",
                source_id="paper_001",
                source_title="Attention Is All You Need",
                text=(
                    "The Transformer allows for significantly more "
                    "parallelization and can reach a new state of the art."
                ),
                page_number=2,
                source_type=SourceType.FULL_TEXT,
            ),
        ],
    )


def test_direct_support_is_not_downgraded_by_other_partial_passages():
    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_101",
                relation=EvidenceRelation.SUPPORTS,
                rationale=(
                    "This passage directly establishes the complete claim."
                ),
            ),
            EvidenceAssessment(
                evidence_id="ev_102",
                relation=EvidenceRelation.PARTIALLY_SUPPORTS,
                rationale=(
                    "This passage establishes only one aspect of the claim."
                ),
            ),
        ],
    )

    assert result.verdict == Verdict.SUPPORTED
    assert result.evidence_strength == result.evidence_strength.__class__.MEDIUM
    assert set(result.supporting_evidence_ids) == {"ev_101", "ev_102"}
    assert any("only partially support" in item for item in result.limitations)


def test_partial_support_alone_remains_partially_supported():
    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_102",
                relation=EvidenceRelation.PARTIALLY_SUPPORTS,
                rationale=(
                    "This passage establishes only one aspect of the claim."
                ),
            )
        ],
    )

    assert result.verdict == Verdict.PARTIALLY_SUPPORTED


def test_direct_support_plus_contradiction_remains_mixed():
    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_101",
                relation=EvidenceRelation.SUPPORTS,
                rationale="This passage directly supports the claim.",
            ),
            EvidenceAssessment(
                evidence_id="ev_102",
                relation=EvidenceRelation.CONTRADICTS,
                rationale="This passage conflicts with the claim.",
            ),
        ],
    )

    assert result.verdict == Verdict.PARTIALLY_SUPPORTED
    assert result.human_review_required is True


def test_partial_support_plus_contradiction_remains_mixed():
    result = decide_verdict(
        make_request(),
        [
            EvidenceAssessment(
                evidence_id="ev_101",
                relation=EvidenceRelation.PARTIALLY_SUPPORTS,
                rationale="This passage supports one aspect of the claim.",
            ),
            EvidenceAssessment(
                evidence_id="ev_102",
                relation=EvidenceRelation.CONTRADICTS,
                rationale="This passage conflicts with the claim.",
            ),
        ],
    )

    assert result.verdict == Verdict.PARTIALLY_SUPPORTED
    assert result.human_review_required is True
