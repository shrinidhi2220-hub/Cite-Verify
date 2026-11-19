
from .enums import (
    Verdict,
    EvidenceStrength,
    EvidenceQualityStatus,
    EvidenceRelation,
    VerificationMethod,
)

from .schemas import (
    VerificationRequest,
    EvidenceAssessment,
    NumericalDiscrepancy,
    VerdictDecision,
)

from .evidence_quality import assess_evidence_quality


def decide_verdict(
    request: VerificationRequest,
    assessments: list[EvidenceAssessment],
    numerical_discrepancies: list[NumericalDiscrepancy] | None = None,
) -> VerdictDecision:

    discrepancies = numerical_discrepancies or []

    quality = assess_evidence_quality(request)

    input_ids = [item.evidence_id for item in assessments]

    if len(input_ids) != len(set(input_ids)):
        raise ValueError(
            "An evidence passage must not be assessed more than once."
        )

    usable_ids = set(quality.usable_evidence_ids)
    unknown_ids = set(input_ids) - usable_ids

    if unknown_ids:
        raise ValueError(
            f"Assessments contain unknown or unusable evidence IDs: "
            f"{sorted(unknown_ids)}"
        )

    limitations = list(request.source_limitations)

    # Evidence must be usable before any verdict is produced.
    if quality.status in {
        EvidenceQualityStatus.AMBIGUOUS_SOURCE,
        EvidenceQualityStatus.INSUFFICIENT_EVIDENCE,
    }:
        return VerdictDecision(
            claim_id=request.claim_id,
            verdict=Verdict.INSUFFICIENT_EVIDENCE,
            explanation=(
                "There is not enough reliable source evidence "
                "to assess this scientific claim."
            ),
            evidence_strength=EvidenceStrength.LOW,
            limitations=limitations + [
                issue.message for issue in quality.issues
            ],
            human_review_required=True,
        )

    if not assessments:
        return VerdictDecision(
            claim_id=request.claim_id,
            verdict=Verdict.INSUFFICIENT_EVIDENCE,
            explanation=(
                "No evidence assessments were supplied. "
                "Scientific claim comparison is required."
            ),
            evidence_strength=EvidenceStrength.LOW,
            limitations=limitations + [
                "Evidence assessment is missing."
            ],
            human_review_required=True,
        )

    support_ids = [
        item.evidence_id
        for item in assessments
        if item.relation == EvidenceRelation.SUPPORTS
    ]

    partial_ids = [
        item.evidence_id
        for item in assessments
        if item.relation == EvidenceRelation.PARTIALLY_SUPPORTS
    ]

    contradiction_ids = [
        item.evidence_id
        for item in assessments
        if item.relation == EvidenceRelation.CONTRADICTS
    ]

    neutral_ids = [
        item.evidence_id
        for item in assessments
        if item.relation in {
            EvidenceRelation.DOES_NOT_ESTABLISH,
            EvidenceRelation.IRRELEVANT,
            EvidenceRelation.UNCERTAIN,
        }
    ]

    has_support = bool(support_ids or partial_ids)
    has_contradiction = bool(contradiction_ids)
    has_uncertainty = any(
        item.relation == EvidenceRelation.UNCERTAIN
        for item in assessments
    )

    # Mixed support and contradiction must not become
    # an oversimplified supported/contradicted result.
    if has_support and has_contradiction:
        verdict = Verdict.PARTIALLY_SUPPORTED
        explanation = (
            "The retrieved evidence contains both supporting "
            "and contradicting findings. The claim needs closer "
            "review of study context and conflicting results."
        )

        limitations.append("Mixed supporting and contradicting evidence.")

    elif has_contradiction:
        verdict = Verdict.CONTRADICTED
        explanation = (
            "The assessed research evidence directly conflicts "
            "with the supplied claim."
        )

    elif partial_ids:
        verdict = Verdict.PARTIALLY_SUPPORTED
        explanation = (
            "The evidence supports some aspects of the claim, "
            "but does not establish the entire statement."
        )

    elif support_ids:
        verdict = Verdict.SUPPORTED
        explanation = (
            "The assessed research evidence directly supports "
            "the supplied claim within the context of the study."
        )

    elif has_uncertainty:
        verdict = Verdict.INSUFFICIENT_EVIDENCE
        explanation = (
            "The evidence assessments are uncertain and do "
            "not support a reliable verification verdict."
        )

    else:
        verdict = Verdict.UNSUPPORTED
        explanation = (
            "The retrieved evidence does not establish "
            "the supplied scientific claim."
        )

    # A numerical discrepancy is a warning, not proof
    # of contradiction. Downgrade a supported result
    # until the discrepancy is reviewed.
    if discrepancies and verdict == Verdict.SUPPORTED:
        verdict = Verdict.PARTIALLY_SUPPORTED
        explanation = (
            "The evidence appears relevant, but numerical "
            "differences were detected. The claim requires "
            "contextual review before it can be considered supported."
        )

    if discrepancies:
        limitations.append(
            "Numerical discrepancies require review of units, "
            "study population, methods and experimental conditions."
        )

    if quality.status == EvidenceQualityStatus.ABSTRACT_ONLY:
        limitations.append(
            "Only abstract-level evidence is available. "
            "Full-text review is recommended."
        )

    if has_uncertainty:
        limitations.append(
            "At least one evidence passage has an uncertain relationship."
        )

    # This is a transparent heuristic, not a calibrated probability.
    if quality.status == EvidenceQualityStatus.ABSTRACT_ONLY:
        strength = EvidenceStrength.LOW

    elif verdict in {
        Verdict.SUPPORTED,
        Verdict.CONTRADICTED,
    }:
        strength = EvidenceStrength.HIGH

    elif verdict == Verdict.INSUFFICIENT_EVIDENCE:
        strength = EvidenceStrength.LOW

    else:
        strength = EvidenceStrength.MEDIUM

    return VerdictDecision(
        claim_id=request.claim_id,
        verdict=verdict,
        explanation=explanation,

        supporting_evidence_ids=support_ids + partial_ids,
        contradicting_evidence_ids=contradiction_ids,
        neutral_evidence_ids=neutral_ids,

        numerical_discrepancies=discrepancies,

        evidence_strength=strength,
        limitations=list(dict.fromkeys(limitations)),

        # Keep human review enabled for all academic verdicts.
        human_review_required=True,

        method=VerificationMethod.RULE_BASED,
    )
