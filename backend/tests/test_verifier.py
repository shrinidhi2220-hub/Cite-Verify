
from backend.app.verification.enums import (
    Verdict,
    SourceType,
    RetrievalStatus,
    EvidenceQualityStatus,
)

from backend.app.verification.schemas import (
    VerificationRequest,
    EvidencePassage,
)

from backend.app.verification.verifier import verify_claim

from backend.app.verification.evidence_quality import (
    assess_evidence_quality,
)


# ==========================================
# PHASE 1 TESTS — VERIFICATION FOUNDATION
# ==========================================

def test_missing_evidence():

    request = VerificationRequest(
        claim_id="claim_001",
        claim_text="Treatment X reduces disease progression.",
        evidence=[],
        retrieval_status=RetrievalStatus.NOT_FOUND,
    )

    result = verify_claim(request)

    assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE
    assert result.human_review_required is True


def test_full_text_evidence_is_not_assumed_to_support_claim():

    request = VerificationRequest(
        claim_id="claim_002",
        claim_text="Treatment X reduced disease progression by 40%.",
        evidence=[
            EvidencePassage(
                evidence_id="ev_001",
                source_id="paper_001",
                text="The experimental group showed a 40% reduction.",
                page_number=5,
                source_type=SourceType.FULL_TEXT,
            )
        ],
        retrieval_status=RetrievalStatus.FULL_TEXT_AVAILABLE,
    )

    result = verify_claim(request)

    assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE
    assert result.reviewed_evidence_ids == ["ev_001"]
    assert "semantic_analysis_pending" in result.warnings


def test_ambiguous_source_is_not_marked_contradicted():

    request = VerificationRequest(
        claim_id="claim_003",
        claim_text="Research supports treatment X.",
        evidence=[],
        retrieval_status=RetrievalStatus.AMBIGUOUS,
    )

    result = verify_claim(request)

    assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE
    assert result.human_review_required is True


# ==========================================
# PHASE 2 TESTS — EVIDENCE QUALITY ENGINE
# ==========================================

def test_metadata_only_is_not_usable():

    request = VerificationRequest(
        claim_id="claim_004",
        claim_text="Research proves treatment X is effective.",
        retrieval_status=RetrievalStatus.METADATA_ONLY,
        evidence=[
            EvidencePassage(
                evidence_id="ev_004",
                source_id="paper_004",
                text="",
                source_type=SourceType.METADATA_ONLY,
            )
        ],
    )

    result = assess_evidence_quality(request)

    assert result.status == EvidenceQualityStatus.INSUFFICIENT_EVIDENCE
    assert result.usable_evidence_ids == []


def test_abstract_only_is_detected():

    request = VerificationRequest(
        claim_id="claim_005",
        claim_text="Treatment X reduces disease progression.",
        evidence=[
            EvidencePassage(
                evidence_id="ev_005",
                source_id="paper_005",
                text="The study observed improvement in the experimental group.",
                source_type=SourceType.ABSTRACT,
            )
        ],
    )

    result = assess_evidence_quality(request)

    assert result.status == EvidenceQualityStatus.ABSTRACT_ONLY
    assert result.abstract_evidence_ids == ["ev_005"]


def test_duplicate_evidence_ids_are_excluded():

    request = VerificationRequest(
        claim_id="claim_006",
        claim_text="Treatment X improves recovery.",
        evidence=[
            EvidencePassage(
                evidence_id="ev_duplicate",
                source_id="paper_006",
                text="First passage from the study.",
                source_type=SourceType.FULL_TEXT,
            ),
            EvidencePassage(
                evidence_id="ev_duplicate",
                source_id="paper_007",
                text="Second passage from another study.",
                source_type=SourceType.FULL_TEXT,
            ),
        ],
    )

    result = assess_evidence_quality(request)

    assert result.duplicate_evidence_ids == ["ev_duplicate"]
    assert result.usable_evidence_ids == []


def test_full_text_without_page_number_is_flagged():

    request = VerificationRequest(
        claim_id="claim_007",
        claim_text="Treatment X improves recovery.",
        evidence=[
            EvidencePassage(
                evidence_id="ev_007",
                source_id="paper_007",
                text="The study showed improved recovery.",
                source_type=SourceType.FULL_TEXT,
            )
        ],
    )

    result = assess_evidence_quality(request)

    assert result.status == EvidenceQualityStatus.FULL_TEXT_AVAILABLE

    issue_codes = [
        issue.code for issue in result.issues
    ]

    assert "evidence_location_missing" in issue_codes
