import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..verification.schemas import VerificationRequest, VerdictDecision
from ..verification.ai_reasoner import GeminiAssessmentError
from ..services.verification_service import verify_claim_end_to_end
from ..services.research_evidence_service import prepare_research_evidence
from ..retrieval.research_models import ResearchEvidenceRequest


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/verification", tags=["Verification"])


class VerificationJobAccepted(BaseModel):
    job_id: str
    status: Literal["queued"]
    status_url: str
    message: str


class VerificationJobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    stage: Literal["queued", "research", "ai_reasoning", "completed", "failed"] = "queued"
    result: VerdictDecision | None = None
    error: str | None = None
    error_code: str | None = None
    retryable: bool = False
    retry_available: bool = False
    retry_of_job_id: str | None = None
    research_summary: dict[str, Any] | None = None


# By default, persist outside the repository so research evidence and job data
# are not accidentally committed. Override with CITEVERIFY_JOB_STORE_PATH.
_DEFAULT_JOB_STORE = Path.home() / ".citeverify" / "verification_jobs.json"
JOB_STORE_PATH = Path(os.getenv("CITEVERIFY_JOB_STORE_PATH", str(_DEFAULT_JOB_STORE))).expanduser()
MAX_PERSISTED_JOBS = 100
_jobs_lock = Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist_jobs_locked() -> None:
    """Atomically persist the job registry. Caller must hold _jobs_lock."""
    try:
        JOB_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(
            _jobs.items(),
            key=lambda item: item[1].get("created_at", ""),
        )[-MAX_PERSISTED_JOBS:]
        payload = {job_id: job for job_id, job in ordered}
        temporary_path = JOB_STORE_PATH.with_suffix(JOB_STORE_PATH.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_path, JOB_STORE_PATH)
    except Exception:
        # Keep the in-memory job alive; report the persistence failure loudly.
        logger.exception("Could not persist CiteVerify verification jobs to %s", JOB_STORE_PATH)


def _load_jobs() -> dict[str, dict[str, Any]]:
    if not JOB_STORE_PATH.is_file():
        return {}

    try:
        loaded = json.loads(JOB_STORE_PATH.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("Job store root must be a JSON object.")

        # BackgroundTasks cannot resume after a process restart. Mark interrupted
        # jobs failed, but retain their serialized VerificationRequest for retry.
        recovered = False
        for job in loaded.values():
            if not isinstance(job, dict):
                continue
            if job.get("status") in {"queued", "running"}:
                job["status"] = "failed"
                job["stage"] = "failed"
                job["error_code"] = "SERVER_RESTARTED"
                job["retryable"] = False
                if job.get("verification_request"):
                    job["error"] = (
                        "The API restarted while this job was running. "
                        "Its retrieved evidence was saved; retry the AI assessment."
                    )
                else:
                    job["error"] = (
                        "The API restarted before research evidence was saved. "
                        "Start a new verification to repeat retrieval."
                    )
                job["updated_at"] = _utc_now()
                recovered = True

        if recovered:
            # Persist recovered terminal states immediately.
            global _jobs
            _jobs = loaded
            with _jobs_lock:
                _persist_jobs_locked()

        return loaded
    except Exception:
        logger.exception("Could not load CiteVerify job store from %s", JOB_STORE_PATH)
        return {}


_jobs: dict[str, dict[str, Any]] = {}
_jobs = _load_jobs()


def _new_job_record(
    *,
    verification_request: dict[str, Any] | None = None,
    research_summary: dict[str, Any] | None = None,
    retry_of_job_id: str | None = None,
    stage: str = "queued",
    retry_count: int = 0,
) -> dict[str, Any]:
    now = _utc_now()
    return {
        "status": "queued",
        "stage": stage,
        "result": None,
        "error": None,
        "error_code": None,
        "retryable": False,
        "verification_request": verification_request,
        "research_summary": research_summary,
        "retry_of_job_id": retry_of_job_id,
        "retry_count": retry_count,
        "created_at": now,
        "updated_at": now,
    }


def _update_job(job_id: str, **updates: Any) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(updates)
        job["updated_at"] = _utc_now()
        _persist_jobs_locked()


def _mark_job_failed(
    job_id: str,
    *,
    error: str,
    error_code: str = "VERIFICATION_ERROR",
    retryable: bool = False,
) -> None:
    _update_job(
        job_id,
        status="failed",
        stage="failed",
        error=error,
        error_code=error_code,
        retryable=retryable,
    )


def _mark_gemini_failed(job_id: str, exc: GeminiAssessmentError) -> None:
    if exc.error_code == "RESOURCE_EXHAUSTED":
        message = (
            "Gemini reported RESOURCE_EXHAUSTED. Retrieved research and evidence "
            "were saved. Check the Google project quota, then use Retry AI assessment."
        )
    elif exc.error_code == "INTERNAL":
        message = (
            "Gemini reported a temporary INTERNAL error after bounded retry attempts. "
            "Retrieved research and evidence were saved; you can retry the AI assessment."
        )
    else:
        message = (
            f"Gemini assessment failed ({exc.error_code}). Retrieved research and "
            "evidence were saved; inspect the provider configuration before retrying."
        )
    _mark_job_failed(
        job_id,
        error=message,
        error_code=exc.error_code,
        retryable=exc.retryable,
    )


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError("Expected a Pydantic model or dictionary.")


def _execute_verification_job(job_id: str, request: VerificationRequest) -> None:
    _update_job(job_id, status="running", stage="ai_reasoning")
    logger.info("Verification job started: %s", job_id)

    try:
        result = verify_claim_end_to_end(request)
        _update_job(
            job_id,
            status="completed",
            stage="completed",
            result=_model_dump(result),
            error=None,
            error_code=None,
            retryable=False,
        )
        logger.info("Verification job completed: %s", job_id)
    except GeminiAssessmentError as exc:
        logger.exception("Gemini assessment failed for job: %s", job_id)
        _mark_gemini_failed(job_id, exc)
    except ValueError as exc:
        logger.warning("Verification validation failed for job %s: %s", job_id, exc, exc_info=True)
        _mark_job_failed(job_id, error=str(exc), error_code="VALIDATION_ERROR")
    except RuntimeError:
        logger.exception("Verification AI service failed for job: %s", job_id)
        _mark_job_failed(
            job_id,
            error="AI verification service is unavailable or timed out. The saved request is available for a manual retry.",
            error_code="VERIFICATION_ERROR",
        )
    except Exception:
        logger.exception("Unexpected verification error for job: %s", job_id)
        _mark_job_failed(job_id, error="An unexpected verification error occurred.")


@router.post("/run", response_model=VerificationJobAccepted, status_code=202)
def run_verification(request: VerificationRequest, background_tasks: BackgroundTasks):
    job_id = uuid4().hex
    record = _new_job_record(verification_request=_model_dump(request), stage="ai_reasoning")
    with _jobs_lock:
        _jobs[job_id] = record
        _persist_jobs_locked()

    background_tasks.add_task(_execute_verification_job, job_id, request)
    logger.info("Verification job queued: %s", job_id)
    return VerificationJobAccepted(
        job_id=job_id,
        status="queued",
        status_url=f"/api/v1/verification/status/{job_id}",
        message="Verification started. Check the status endpoint for the result.",
    )


def _execute_research_verification_job(job_id: str, request: ResearchEvidenceRequest) -> None:
    _update_job(job_id, status="running", stage="research")
    logger.info("Research verification job started: %s", job_id)

    try:
        prepared = prepare_research_evidence(request)
        verification_request = prepared.verification_request
        summary = prepared.model_dump(mode="json", exclude={"verification_request"})
        summary["evidence"] = [
            passage.model_dump(mode="json")
            for passage in verification_request.evidence
            if passage.text.strip()
        ]

        # Save both the user request and the exact prepared evidence before
        # calling Gemini. A provider failure must not discard retrieval work.
        _update_job(
            job_id,
            stage="ai_reasoning",
            verification_request=_model_dump(verification_request),
            research_request=_model_dump(request),
            research_summary=summary,
        )

        result = verify_claim_end_to_end(verification_request)
        _update_job(
            job_id,
            status="completed",
            stage="completed",
            result=_model_dump(result),
            error=None,
            error_code=None,
            retryable=False,
        )
        logger.info("Research verification job completed: %s", job_id)

    except GeminiAssessmentError as exc:
        logger.exception("Gemini assessment failed for research job: %s", job_id)
        _mark_gemini_failed(job_id, exc)
    except ValueError as exc:
        logger.warning("Research verification input failed for job %s: %s", job_id, exc, exc_info=True)
        _mark_job_failed(job_id, error=str(exc), error_code="VALIDATION_ERROR")
    except RuntimeError:
        logger.exception("Research retrieval or verification failed for job: %s", job_id)
        _mark_job_failed(
            job_id,
            error=(
                "Research retrieval or AI verification failed. "
                "If evidence was already retrieved, it remains saved for retry."
            ),
            error_code="RESEARCH_OR_VERIFICATION_ERROR",
        )
    except Exception:
        logger.exception("Unexpected research verification failure: %s", job_id)
        _mark_job_failed(
            job_id,
            error="An unexpected research verification error occurred.",
            error_code="UNEXPECTED_ERROR",
        )


@router.post("/run-from-research", response_model=VerificationJobAccepted, status_code=202)
def run_verification_from_research(
    request: ResearchEvidenceRequest,
    background_tasks: BackgroundTasks,
):
    job_id = uuid4().hex
    record = _new_job_record(stage="research")
    record["research_request"] = _model_dump(request)
    with _jobs_lock:
        _jobs[job_id] = record
        _persist_jobs_locked()

    background_tasks.add_task(_execute_research_verification_job, job_id, request)
    logger.info("Research verification job queued: %s", job_id)
    return VerificationJobAccepted(
        job_id=job_id,
        status="queued",
        status_url=f"/api/v1/verification/status/{job_id}",
        message="Research retrieval and claim verification started. Check the status endpoint for progress and the final verdict.",
    )


def _execute_retry_job(job_id: str, request: VerificationRequest) -> None:
    _update_job(job_id, status="running", stage="ai_reasoning")
    logger.info("Gemini-only retry started: %s", job_id)
    try:
        result = verify_claim_end_to_end(request)
        _update_job(
            job_id,
            status="completed",
            stage="completed",
            result=_model_dump(result),
            error=None,
            error_code=None,
            retryable=False,
        )
        logger.info("Gemini-only retry completed: %s", job_id)
    except GeminiAssessmentError as exc:
        logger.exception("Gemini-only retry failed: %s", job_id)
        _mark_gemini_failed(job_id, exc)
    except ValueError as exc:
        logger.warning("Retry request validation failed for %s: %s", job_id, exc, exc_info=True)
        _mark_job_failed(job_id, error=str(exc), error_code="VALIDATION_ERROR")
    except Exception:
        logger.exception("Unexpected Gemini-only retry error: %s", job_id)
        _mark_job_failed(
            job_id,
            error="The AI retry failed unexpectedly. Saved research evidence remains available.",
            error_code="RETRY_ERROR",
        )


@router.post("/retry/{job_id}", response_model=VerificationJobAccepted, status_code=202)
def retry_verification(job_id: str, background_tasks: BackgroundTasks):
    """Create a new AI assessment job using previously saved evidence.

    This endpoint never calls prepare_research_evidence, search providers,
    or the PDF downloader. It retries only the verification stage.
    """
    with _jobs_lock:
        original = _jobs.get(job_id)
        if original is None:
            raise HTTPException(status_code=404, detail="Verification job not found.")
        if original.get("status") != "failed":
            raise HTTPException(status_code=409, detail="Only failed jobs can be retried.")
        serialized_request = original.get("verification_request")
        if not serialized_request:
            raise HTTPException(
                status_code=409,
                detail="No prepared evidence was saved for this job. Start a new research verification.",
            )

        retry_count = int(original.get("retry_count", 0))
        if retry_count >= 5:
            raise HTTPException(status_code=429, detail="This verification has reached its manual retry limit.")

        original["retry_count"] = retry_count + 1
        original["updated_at"] = _utc_now()
        retry_request = VerificationRequest.model_validate(serialized_request)
        new_job_id = uuid4().hex
        new_record = _new_job_record(
            verification_request=serialized_request,
            research_summary=original.get("research_summary"),
            retry_of_job_id=job_id,
            stage="ai_reasoning",
            retry_count=retry_count + 1,
        )
        new_record["research_request"] = original.get("research_request")
        _jobs[new_job_id] = new_record
        _persist_jobs_locked()

    background_tasks.add_task(_execute_retry_job, new_job_id, retry_request)
    logger.info("Gemini-only retry queued: %s (original job %s)", new_job_id, job_id)
    return VerificationJobAccepted(
        job_id=new_job_id,
        status="queued",
        status_url=f"/api/v1/verification/status/{new_job_id}",
        message="AI assessment retry started using saved research evidence. Research retrieval was not repeated.",
    )


@router.get("/status/{job_id}", response_model=VerificationJobStatus)
def get_verification_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Verification job not found.")
        snapshot = dict(job)

    return VerificationJobStatus(
        job_id=job_id,
        status=snapshot.get("status", "failed"),
        stage=snapshot.get("stage", "failed"),
        result=snapshot.get("result"),
        error=snapshot.get("error"),
        error_code=snapshot.get("error_code"),
        retryable=bool(snapshot.get("retryable", False)),
        retry_available=bool(snapshot.get("status") == "failed" and snapshot.get("verification_request")),
        retry_of_job_id=snapshot.get("retry_of_job_id"),
        research_summary=snapshot.get("research_summary"),
    )
