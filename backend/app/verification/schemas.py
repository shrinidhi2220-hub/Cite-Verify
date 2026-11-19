
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    Verdict,
    EvidenceStrength,
    SourceType,
    RetrievalStatus,
    VerificationMethod,
    EvidenceQualityStatus,
    EvidenceRelation,
)


class EvidencePassage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    evidence_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_title: str | None = None
    text: str = ""

    page_number: int | None = Field(default=None, ge=1)
    section_name: str | None = None

    source_type: SourceType = SourceType.UNKNOWN
    retrieval_score: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_evidence_text(self):
        if (
            self.source_type in {
                SourceType.FULL_TEXT,
                SourceType.ABSTRACT,
            }
            and not self.text.strip()
        ):
            raise ValueError(
                "Full-text and abstract evidence must contain text."
            )

        return self


class VerificationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)

    citation_ids: list[str] = Field(default_factory=list)
    claim_type: str | None = None

    evidence: list[EvidencePassage] = Field(default_factory=list)

    retrieval_status: RetrievalStatus = RetrievalStatus.RESOLVED
    source_limitations: list[str] = Field(default_factory=list)


class NumericalDiscrepancy(BaseModel):
    claim_value: str
    evidence_value: str
    unit: str | None = None
    description: str


class VerificationResponse(BaseModel):
    claim_id: str
    verdict: Verdict
    explanation: str

    reviewed_evidence_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)

    numerical_discrepancies: list[NumericalDiscrepancy] = Field(
        default_factory=list
    )

    evidence_strength: EvidenceStrength = EvidenceStrength.LOW
    limitations: list[str] = Field(default_factory=list)

    human_review_required: bool = True
    method: VerificationMethod = VerificationMethod.RULE_BASED
    warnings: list[str] = Field(default_factory=list)


class EvidenceIssue(BaseModel):
    code: str
    message: str
    evidence_ids: list[str] = Field(default_factory=list)


class EvidenceQualityResult(BaseModel):
    status: EvidenceQualityStatus

    usable_evidence_ids: list[str] = Field(default_factory=list)
    full_text_evidence_ids: list[str] = Field(default_factory=list)
    abstract_evidence_ids: list[str] = Field(default_factory=list)
    metadata_only_evidence_ids: list[str] = Field(default_factory=list)
    duplicate_evidence_ids: list[str] = Field(default_factory=list)

    issues: list[EvidenceIssue] = Field(default_factory=list)

    human_review_required: bool = True



class EvidenceAssessment(BaseModel):
    evidence_id: str = Field(min_length=1)
    relation: EvidenceRelation
    rationale: str = Field(min_length=1)


class VerdictDecision(BaseModel):
    claim_id: str

    verdict: Verdict
    explanation: str

    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    neutral_evidence_ids: list[str] = Field(default_factory=list)

    numerical_discrepancies: list[NumericalDiscrepancy] = Field(
        default_factory=list
    )

    evidence_strength: EvidenceStrength = EvidenceStrength.LOW

    limitations: list[str] = Field(default_factory=list)

    human_review_required: bool = True
    method: VerificationMethod = VerificationMethod.RULE_BASED



class AIReasoningResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    assessments: list[EvidenceAssessment]

    overall_notes: str = ""

    limitations: list[str] = Field(default_factory=list)
