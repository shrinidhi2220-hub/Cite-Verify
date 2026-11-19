
from backend.app.verification.enums import (
    SourceType,
    RetrievalStatus,
)

from backend.app.verification.schemas import (
    VerificationRequest,
    EvidencePassage,
)

from backend.app.verification.ai_reasoner import (
    assess_with_openai,
)


def main():

    request = VerificationRequest(
        claim_id="openai_demo_001",

        claim_text=(
            "The machine learning model achieved 95% accuracy."
        ),

        citation_ids=["demo_citation_001"],

        claim_type="quantitative",

        retrieval_status=RetrievalStatus.FULL_TEXT_AVAILABLE,

        evidence=[
            EvidencePassage(
                evidence_id="openai_ev_001",
                source_id="openai_paper_001",

                source_title="Synthetic Research Evaluation",

                text=(
                    "The model achieved 95% accuracy "
                    "on the experimental validation dataset."
                ),

                page_number=5,
                section_name="Results",

                source_type=SourceType.FULL_TEXT,

                retrieval_score=0.95,
            )
        ],
    )

    result = assess_with_openai(request)

    print("\nCITEVERIFY OPENAI CONNECTION SUCCESSFUL")

    print("Claim ID:", request.claim_id)

    print("Assessments:", len(result.assessments))

    for item in result.assessments:

        print("\nEvidence ID:", item.evidence_id)

        print("Relationship:", item.relation.value)

        print("Reason:", item.rationale)

    print("\nOverall notes:", result.overall_notes)


if __name__ == "__main__":
    main()
