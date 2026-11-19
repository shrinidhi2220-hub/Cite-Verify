import json

import pytest

from backend.app.verification.enums import (
    SourceType,
    EvidenceRelation,
)
from backend.app.verification.schemas import (
    VerificationRequest,
    EvidencePassage,
)
from backend.app.verification.ai_reasoner import (
    SYSTEM_PROMPT,
    build_user_prompt,
    parse_ai_response,
)


def make_request():
    """Shared two-passage request used by the original and retry tests."""
    return VerificationRequest(
        claim_id="claim_ai_001",
        claim_text="The model achieved 95% accuracy.",
        evidence=[
            EvidencePassage(
                evidence_id="ev_001",
                source_id="paper_001",
                text="The model achieved 95% accuracy.",
                page_number=5,
                source_type=SourceType.FULL_TEXT,
            ),
            EvidencePassage(
                evidence_id="ev_002",
                source_id="paper_001",
                text="The model achieved 90% accuracy.",
                page_number=6,
                source_type=SourceType.FULL_TEXT,
            ),
        ],
    )


def test_system_prompt_exists():
    assert "Never invent research findings" in SYSTEM_PROMPT


def test_build_user_prompt():
    request = make_request()
    prompt = build_user_prompt(request)
    data = json.loads(prompt)

    assert data["claim_id"] == "claim_ai_001"
    assert len(data["evidence"]) == 2


def test_parse_valid_ai_response():
    request = make_request()
    response = {
        "assessments": [
            {
                "evidence_id": "ev_001",
                "relation": "supports",
                "rationale": "The passage reports the same result.",
            },
            {
                "evidence_id": "ev_002",
                "relation": "contradicts",
                "rationale": "The reported accuracy differs.",
            },
        ],
        "overall_notes": "Evidence contains mixed findings.",
        "limitations": ["Study context needs review"],
    }

    result = parse_ai_response(json.dumps(response), request)

    assert len(result.assessments) == 2
    assert result.assessments[0].relation == EvidenceRelation.SUPPORTS


def test_reject_unknown_evidence_id():
    request = make_request()
    response = {
        "assessments": [
            {
                "evidence_id": "unknown_id",
                "relation": "supports",
                "rationale": "Unrecognized evidence.",
            }
        ],
        "overall_notes": "",
        "limitations": [],
    }

    with pytest.raises(ValueError):
        parse_ai_response(json.dumps(response), request)


def test_reject_duplicate_evidence_ids():
    request = make_request()
    response = {
        "assessments": [
            {
                "evidence_id": "ev_001",
                "relation": "supports",
                "rationale": "First assessment.",
            },
            {
                "evidence_id": "ev_001",
                "relation": "contradicts",
                "rationale": "Duplicate assessment.",
            },
        ],
        "overall_notes": "",
        "limitations": [],
    }

    with pytest.raises(ValueError):
        parse_ai_response(json.dumps(response), request)


def test_reject_missing_evidence_assessment():
    request = make_request()
    response = {
        "assessments": [
            {
                "evidence_id": "ev_001",
                "relation": "supports",
                "rationale": "Only one passage assessed.",
            }
        ],
        "overall_notes": "",
        "limitations": [],
    }

    with pytest.raises(ValueError):
        parse_ai_response(json.dumps(response), request)


def test_reject_invalid_json():
    with pytest.raises(ValueError):
        parse_ai_response("This is not valid JSON", make_request())


def test_extracts_retry_metadata_for_transient_and_quota_errors():
    from backend.app.verification.ai_reasoner import (
        _extract_error_code,
        _is_retryable_error,
    )

    transient = RuntimeError(
        "Gemini background task failed: Error(code='INTERNAL')"
    )
    quota = RuntimeError(
        "Gemini background task failed: Error(code='RESOURCE_EXHAUSTED')"
    )

    assert _extract_error_code(transient) == "INTERNAL"
    assert _is_retryable_error(transient) is True
    assert _extract_error_code(quota) == "RESOURCE_EXHAUSTED"
    assert _is_retryable_error(quota) is False


def test_assess_with_gemini_retries_one_transient_internal_failure(monkeypatch):
    from backend.app.verification import ai_reasoner

    request = make_request()
    response = {
        "assessments": [
            {
                "evidence_id": "ev_001",
                "relation": "supports",
                "rationale": "Same reported result.",
            },
            {
                "evidence_id": "ev_002",
                "relation": "contradicts",
                "rationale": "Different reported result.",
            },
        ],
        "overall_notes": "Mixed evidence.",
        "limitations": [],
    }
    calls = {"count": 0}

    def fake_interaction(_client, _model, _prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError(
                "Error(code='INTERNAL', message='temporary provider failure')"
            )
        return json.dumps(response)

    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MAX_ATTEMPTS", "2")
    monkeypatch.setattr(ai_reasoner.genai, "Client", lambda api_key: object())
    monkeypatch.setattr(
        ai_reasoner,
        "_run_gemini_background_interaction",
        fake_interaction,
    )
    monkeypatch.setattr(ai_reasoner.time, "sleep", lambda _delay: None)

    result = ai_reasoner.assess_with_gemini(request)

    assert calls["count"] == 2
    assert len(result.assessments) == 2


def test_assess_with_gemini_does_not_auto_retry_resource_exhausted(monkeypatch):
    from backend.app.verification import ai_reasoner

    request = make_request()
    calls = {"count": 0}

    def fake_interaction(_client, _model, _prompt):
        calls["count"] += 1
        raise RuntimeError(
            "Error(code='RESOURCE_EXHAUSTED', message='quota reached')"
        )

    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MAX_ATTEMPTS", "3")
    monkeypatch.setattr(ai_reasoner.genai, "Client", lambda api_key: object())
    monkeypatch.setattr(
        ai_reasoner,
        "_run_gemini_background_interaction",
        fake_interaction,
    )

    with pytest.raises(ai_reasoner.GeminiAssessmentError) as exc_info:
        ai_reasoner.assess_with_gemini(request)

    assert calls["count"] == 1
    assert exc_info.value.error_code == "RESOURCE_EXHAUSTED"
    assert exc_info.value.retryable is False
