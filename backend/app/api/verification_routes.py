
import logging
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

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


# --------------------------------------------------
# JOB RESPONSE SCHEMAS
# --------------------------------------------------

class VerificationJobAccepted(BaseModel):
    job_id: str
    status: Literal["queued"]
    status_url: str
    message: str


class VerificationJobStatus(BaseModel):
    job_id: str
    status: Literal[
        "queued",
        "running",
        "completed",
        "failed",
    ]
    result: VerdictDecision | None = None
    error: str | None = None


# --------------------------------------------------
# IN-MEMORY JOB STORAGE
# --------------------------------------------------

# Suitable for the current single-process hackathon demo.
# Jobs are lost when the server restarts.

_jobs: dict[str, dict[str, Any]] = {}

_jobs_lock = Lock()


# --------------------------------------------------
# BACKGROUND VERIFICATION WORKER
# --------------------------------------------------

def _execute_verification_job(
    job_id: str,
    request: VerificationRequest,
) -> None:
    """
    Execute the complete verification pipeline in the
    background without blocking the initial HTTP response.
    """

    with _jobs_lock:
        if job_id not in _jobs:
            return

        _jobs[job_id]["status"] = "running"

    logger.info(
        "Verification job started: %s",
        job_id,
    )

    try:
        result = verify_claim_end_to_end(request)

        with _jobs_lock:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["result"] = result
            _jobs[job_id]["error"] = None

        logger.info(
            "Verification job completed: %s",
            job_id,
        )

    except ValueError as exc:
        logger.warning(
            "Verification job validation failed: %s",
            job_id,
            exc_info=True,
        )

        with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(exc)

    except RuntimeError:
        logger.exception(
            "Verification AI service failed for job: %s",
            job_id,
        )

        with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = (
                "AI verification service is unavailable "
                "or timed out. Please try again."
            )

    except Exception:
        logger.exception(
            "Unexpected verification error for job: %s",
            job_id,
        )

        with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = (
                "An unexpected verification error occurred."
            )


# --------------------------------------------------
# POST: START VERIFICATION
# --------------------------------------------------

@router.post(
    "/run",
    response_model=VerificationJobAccepted,
    status_code=202,
)
def run_verification(
    request: VerificationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start scientific claim verification.

    Returns a job ID immediately.
    The client can poll the status endpoint for the result.
    """

    job_id = uuid4().hex

    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "result": None,
            "error": None,
        }

    background_tasks.add_task(
        _execute_verification_job,
        job_id,
        request,
    )

    logger.info(
        "Verification job queued: %s",
        job_id,
    )

    return VerificationJobAccepted(
        job_id=job_id,
        status="queued",
        status_url=(
            f"/api/v1/verification/status/{job_id}"
        ),
        message=(
            "Verification started. "
            "Check the status endpoint for the result."
        ),
    )


# --------------------------------------------------
# GET: CHECK VERIFICATION STATUS
# --------------------------------------------------

@router.get(
    "/status/{job_id}",
    response_model=VerificationJobStatus,
)
def get_verification_status(job_id: str):
    """
    Retrieve the current state and result of a verification job.
    """

    with _jobs_lock:
        job = _jobs.get(job_id)

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Verification job not found.",
            )

        # Copy the record while holding the lock.
        snapshot = job.copy()

    return VerificationJobStatus(
        job_id=job_id,
        status=snapshot["status"],
        result=snapshot["result"],
        error=snapshot["error"],
    )
