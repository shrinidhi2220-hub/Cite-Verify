import logging

from fastapi import APIRouter, HTTPException

from ..retrieval.research_models import (
    ResearchEvidenceRequest,
    ResearchEvidencePreparation,
)
from ..services.research_evidence_service import prepare_research_evidence

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/research",
    tags=["Research Retrieval"],
)


@router.post(
    "/prepare",
    response_model=ResearchEvidencePreparation,
)
def prepare_evidence_for_verification(
    request: ResearchEvidenceRequest,
) -> ResearchEvidencePreparation:
    """Find research, retrieve relevant passages and return a Member 3 request.

    The response's verification_request can be submitted to
    POST /api/v1/verification/run.
    """
    try:
        return prepare_research_evidence(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Research evidence preparation failed")
        raise HTTPException(
            status_code=502,
            detail="Research retrieval service failed. Check provider availability and retry.",
        ) from exc
