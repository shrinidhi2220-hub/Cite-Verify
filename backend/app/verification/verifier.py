
from .enums import (
    Verdict,
    EvidenceStrength,
    RetrievalStatus,
    EvidenceQualityStatus,
    VerificationMethod,
)

from .schemas import (
    VerificationRequest,
    VerificationResponse,
)

from .evidence_quality import assess_evidence_quality


class VerificationEngine:

    def verify(
        self,
        request: VerificationRequest,
    ) -> VerificationResponse:

        quality = assess_evidence_quality(request)

        warnings = [
            issue.code for issue in quality.issues
        ]

        limitations = list(request.source_limitations)

        limitations.extend(
            issue.message for issue in quality.issues
        )

        if quality.status == EvidenceQualityStatus.AMBIGUOUS_SOURCE:
            explanation = (
                "The research source identity is ambiguous. "
                "Human review is required before verification."
            )

        elif request.retrieval_status == RetrievalStatus.NOT_FOUND:
            explanation = (
                "The cited research publication could not be located."
            )

        elif quality.status == EvidenceQualityStatus.INSUFFICIENT_EVIDENCE:
            explanation = (
                "Available information does not contain usable "
                "scientific evidence passages."
            )

        elif quality.status == EvidenceQualityStatus.ABSTRACT_ONLY:
            explanation = (
                "Only abstract-level evidence is available. "
                "Full-text comparison is recommended."
            )

        else:
            explanation = (
                "Full-text research evidence is available. "
                "Semantic claim-to-evidence comparison "
                "is pending in the next development phase."
            )

            warnings.append("semantic_analysis_pending")

        limitations.append(
            "Evidence quality is assessed, but scientific "
            "claim support has not yet been established."
        )

        return VerificationResponse(
            claim_id=request.claim_id,

            verdict=Verdict.INSUFFICIENT_EVIDENCE,

            explanation=explanation,

            reviewed_evidence_ids=quality.usable_evidence_ids,

            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],

            numerical_discrepancies=[],

            evidence_strength=EvidenceStrength.LOW,

            limitations=limitations,

            human_review_required=True,

            method=VerificationMethod.RULE_BASED,

            warnings=list(dict.fromkeys(warnings)),
        )


def verify_claim(
    request: VerificationRequest,
) -> VerificationResponse:

    engine = VerificationEngine()

    return engine.verify(request)
