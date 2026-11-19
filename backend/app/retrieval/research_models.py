from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..verification.enums import RetrievalStatus
from ..verification.schemas import VerificationRequest


class ResearchEvidenceRequest(BaseModel):
    """Input for finding cited research and preparing verification evidence."""

    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)

    # Use a query, title, or DOI from the document's reference list.
    search_query: str | None = None
    citation_title: str | None = None
    citation_doi: str | None = None
    citation_authors: list[str] = Field(default_factory=list)
    publication_year: int | None = Field(default=None, ge=1600, le=2200)
    citation_ids: list[str] = Field(default_factory=list)
    claim_type: str | None = None

    per_page: int = Field(default=5, ge=1, le=20)
    top_k: int = Field(default=5, ge=1, le=20)
    max_papers: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def require_search_reference(self):
        if not any((self.search_query, self.citation_title, self.citation_doi)):
            raise ValueError(
                "Provide search_query, citation_title, or citation_doi."
            )
        return self


class ResearchEvidencePreparation(BaseModel):
    search_status: str
    citation_match_status: str
    papers_found: int
    papers_processed: int
    evidence_count: int
    retrieval_status: RetrievalStatus
    source_limitations: list[str] = Field(default_factory=list)
    papers: list[dict[str, Any]] = Field(default_factory=list)
    verification_request: VerificationRequest
