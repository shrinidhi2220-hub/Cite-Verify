
import logging

from fastapi import APIRouter, HTTPException



from ..verification.schemas import (
    VerificationRequest,
    VerdictDecision,
)

from ..services.verification_service import (
    verify_claim_end_to_end,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/verification",
    tags=["Verification"],
)


@router.post("/run", response_model=VerdictDecision)
def run_verification(request: VerificationRequest):
    """
    Verify a scientific claim against supplied research evidence.
    """

    try:
        result = verify_claim_end_to_end(request)
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        logger.exception("Verification AI service failed")

        raise HTTPException(
            status_code=503,
            detail=(
                "Verification service is currently unavailable. "
                "Check the AI configuration and retry."
            ),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected verification error")

        raise HTTPException(
            status_code=500,
            detail="An unexpected verification error occurred.",
        ) from exc
