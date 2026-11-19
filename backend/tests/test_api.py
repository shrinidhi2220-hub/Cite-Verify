
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import verification_routes

from backend.app.verification.enums import Verdict

from backend.app.verification.schemas import VerdictDecision


client = TestClient(app)


def test_health_endpoint():

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_verification_endpoint(monkeypatch):

    def fake_verification(request):

        return VerdictDecision(
            claim_id=request.claim_id,
            verdict=Verdict.SUPPORTED,
            explanation="Test evidence supports this claim.",
        )

    monkeypatch.setattr(
        verification_routes,
        "verify_claim_end_to_end",
        fake_verification,
    )

    payload = {
        "claim_id": "claim_api_001",
        "claim_text": "The model achieved 95% accuracy.",
        "retrieval_status": "full_text_available",
        "evidence": [
            {
                "evidence_id": "ev_api_001",
                "source_id": "paper_api_001",
                "text": "The model achieved 95% accuracy.",
                "page_number": 5,
                "source_type": "full_text",
            }
        ],
    }

    # Start the asynchronous verification job.
    response = client.post(
        "/api/v1/verification/run",
        json=payload,
    )

    assert response.status_code == 202

    job = response.json()

    assert job["job_id"]
    assert job["status"] == "queued"
    assert job["status_url"]

    # TestClient waits for the background task to finish.
    status_response = client.get(
        f"/api/v1/verification/status/{job['job_id']}"
    )

    assert status_response.status_code == 200

    result = status_response.json()

    assert result["status"] == "completed"
    assert result["result"]["claim_id"] == "claim_api_001"
    assert result["result"]["verdict"] == "SUPPORTED"
    assert result["result"]["explanation"] == (
        "Test evidence supports this claim."
    )
    assert result["error"] is None


def test_ai_service_failure_is_reported_in_job_status(monkeypatch):

    def failing_verification(request):
        raise RuntimeError("Simulated AI service failure")

    monkeypatch.setattr(
        verification_routes,
        "verify_claim_end_to_end",
        failing_verification,
    )

    payload = {
        "claim_id": "claim_api_002",
        "claim_text": "Scientific claim for testing.",
        "evidence": [
            {
                "evidence_id": "ev_api_002",
                "source_id": "paper_api_002",
                "text": "Research passage for testing.",
                "page_number": 2,
                "source_type": "full_text",
            }
        ],
    }

    # Starting the job should return HTTP 202,
    # even if verification later fails.
    response = client.post(
        "/api/v1/verification/run",
        json=payload,
    )

    assert response.status_code == 202

    job = response.json()

    assert job["job_id"]
    assert job["status"] == "queued"

    # The actual failure is reported through the status endpoint.
    status_response = client.get(
        f"/api/v1/verification/status/{job['job_id']}"
    )

    assert status_response.status_code == 200

    result = status_response.json()

    assert result["status"] == "failed"
    assert result["result"] is None
    assert "unavailable" in result["error"].lower()


def test_unknown_verification_job_returns_404():

    response = client.get(
        "/api/v1/verification/status/nonexistent_job"
    )

    assert response.status_code == 404
