
from ..verification.enums import (
    EvidenceQualityStatus,
    VerificationMethod,
)

from ..verification.schemas import (
    VerificationRequest,
    VerdictDecision,
)

from ..verification.evidence_quality import (
    assess_evidence_quality,
)

from ..verification.ai_reasoner import (
    assess_with_gemini,
)

from ..verification.numerical_checker import (
    compare_claim_to_evidence,
)

from ..verification.verdict_engine import (
    decide_verdict,
)


def verify_claim_end_to_end(
    request: VerificationRequest,
) -> VerdictDecision:
    """
    Complete CiteVerify claim verification pipeline.

    1. Validate evidence quality.
    2. Ask Gemini to assess each evidence passage.
    3. Check numerical discrepancies.
    4. Generate deterministic verdict.
    5. Return an explainable result.
    """

    quality = assess_evidence_quality(request)

    # Never call AI when evidence is insufficient.
    if quality.status in {
        EvidenceQualityStatus.AMBIGUOUS_SOURCE,
        EvidenceQualityStatus.INSUFFICIENT_EVIDENCE,
    }:
        return decide_verdict(request, [])

    # Stage 1: AI evidence assessment.
    ai_result = assess_with_gemini(request)

    # Stage 2: Numerical comparison.
    discrepancies = []
    usable_ids = set(quality.usable_evidence_ids)

    for passage in request.evidence:

        if passage.evidence_id not in usable_ids:
            continue

        if not passage.text.strip():
            continue

        passage_discrepancies = compare_claim_to_evidence(
            request.claim_text,
            passage.text,
        )

        discrepancies.extend(passage_discrepancies)

    # Remove identical duplicate discrepancy records.
    unique_discrepancies = []
    seen = set()

    for item in discrepancies:
        key = (
            item.claim_value,
            item.evidence_value,
            item.unit,
            item.description,
        )

        if key not in seen:
            seen.add(key)
            unique_discrepancies.append(item)

    # Stage 3: Deterministic final verdict.
    decision = decide_verdict(
        request=request,
        assessments=ai_result.assessments,
        numerical_discrepancies=unique_discrepancies,
    )

    # Include AI's explanation and limitations.
    if ai_result.overall_notes:
        decision.explanation += (
            " AI assessment summary: "
            + ai_result.overall_notes
        )

    decision.limitations.extend(ai_result.limitations)

    decision.limitations = list(
        dict.fromkeys(decision.limitations)
    )

    decision.method = VerificationMethod.LLM_ASSISTED

    # Academic decisions must remain reviewable.
    decision.human_review_required = True

    return decision
