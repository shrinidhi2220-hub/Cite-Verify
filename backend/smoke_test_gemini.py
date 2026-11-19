
from backend.app.verification.enums import (
    SourceType,
    RetrievalStatus,
)

from backend.app.verification.schemas import (
    VerificationRequest,
    EvidencePassage,
)

from backend.app.verification.ai_reasoner import (
    assess_with_gemini,
)


def main():
    request = VerificationRequest(
        claim_id="demo_claim_001",
        claim_text=(
            "The machine learning model achieved "
            "95% accuracy."
        ),
        retrieval_status=RetrievalStatus.FULL_TEXT_AVAILABLE,
        evidence=[
            EvidencePassage(
                evidence_id="demo_ev_001",
                source_id="demo_paper_001",
                source_title="Synthetic Research Evaluation",
                text=(
                    "The model achieved an accuracy of 95% "
                    "on the experimental validation dataset."
                ),
                page_number=5,
                section_name="Results",
                source_type=SourceType.FULL_TEXT,
            )
        ],
    )

    result = assess_with_gemini(request)

    print("\nCITEVERIFY GEMINI CONNECTION SUCCESSFUL")
    print("Claim ID:", request.claim_id)
    print("Assessments:", len(result.assessments))

    for item in result.assessments:
        print("\nEvidence ID:", item.evidence_id)
        print("Relationship:", item.relation.value)
        print("Reason:", item.rationale)

    print("\nOverall notes:", result.overall_notes)


if __name__ == "__main__":
    main()
