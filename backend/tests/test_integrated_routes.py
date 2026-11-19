from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_document_and_research_routes_are_registered():
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/v1/documents/upload" in paths
    assert "/api/v1/research/prepare" in paths
    assert "/api/v1/verification/run-from-research" in paths
    assert "/api/v1/verification/run" in paths
    assert "/api/v1/verification/status/{job_id}" in paths
