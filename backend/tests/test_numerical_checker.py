
from backend.app.verification.numerical_checker import (
    extract_numeric_mentions,
    compare_claim_to_evidence,
)


def test_detects_accuracy_percentage_mismatch():

    claim = "The model achieved 95% accuracy."

    evidence = "The model achieved 82% accuracy."

    result = compare_claim_to_evidence(claim, evidence)

    assert len(result) == 1
    assert result[0].claim_value == "95.0"
    assert result[0].evidence_value == "82.0"
    assert result[0].unit == "%"


def test_matching_percentage_is_not_flagged():

    claim = "The model achieved 95% accuracy."

    evidence = "The model achieved 95% accuracy."

    result = compare_claim_to_evidence(claim, evidence)

    assert result == []


def test_accuracy_and_precision_are_not_mixed():

    claim = "The model achieved 95% accuracy."

    evidence = "The model achieved 82% precision."

    result = compare_claim_to_evidence(claim, evidence)

    assert result == []


def test_detects_sample_size_mismatch():

    claim = "The study included 200 patients."

    evidence = "The study included 150 patients."

    result = compare_claim_to_evidence(claim, evidence)

    assert len(result) == 1
    assert result[0].claim_value == "200.0"
    assert result[0].evidence_value == "150.0"


def test_detects_duration_mismatch():

    claim = "The experiment lasted 12 months."

    evidence = "The experiment lasted 6 months."

    result = compare_claim_to_evidence(claim, evidence)

    assert len(result) == 1
    assert result[0].claim_value == "12.0"
    assert result[0].evidence_value == "6.0"


def test_matching_duration_is_not_flagged():

    claim = "The experiment lasted 12 months."

    evidence = "The experiment lasted 12 months."

    result = compare_claim_to_evidence(claim, evidence)

    assert result == []


def test_extracts_scientific_measurements():

    text = (
        "The patient showed 120 mmHg blood pressure "
        "and 75 bpm heart rate."
    )

    result = extract_numeric_mentions(text)

    units = {item.unit for item in result.mentions}

    assert "mmhg" in units
    assert "bpm" in units
