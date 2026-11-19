from backend.app.services import research_evidence_service as service
from backend.app.retrieval.research_models import ResearchEvidenceRequest


def _base_request(**overrides):
    values = {
        "claim_id": "claim-real-001",
        "claim_text": "The intervention improved test accuracy by 12 percent.",
        "citation_title": "A Study of Model Accuracy",
        "citation_doi": "10.1234/example.001",
        "citation_ids": ["[1]"],
    }
    values.update(overrides)
    return ResearchEvidenceRequest(**values)


def test_prepares_full_text_evidence_for_member3(monkeypatch):
    paper = {
        "openalex_id": "https://openalex.org/W123",
        "title": "A Study of Model Accuracy",
        "doi": "https://doi.org/10.1234/example.001",
        "publication_year": 2024,
        "authors": ["A. Researcher"],
        "pdf_url": "https://example.org/paper.pdf",
        "sources": ["openalex"],
    }
    monkeypatch.setattr(
        service,
        "search_academic_papers",
        lambda **kwargs: {
            "status": "SUCCESS",
            "papers": [paper],
            "source_status": {"openalex": {"status": "SUCCESS"}},
        },
    )
    monkeypatch.setattr(
        service,
        "download_paper",
        lambda pdf_url, paper_id: {
            "status": "FULL TEXT AVAILABLE",
            "file_path": "fake-paper.pdf",
            "reason": "downloaded",
        },
    )
    monkeypatch.setattr(
        service,
        "extract_pdf_text",
        lambda path: {
            "status": "SUCCESS",
            "pages": [{
                "page_number": 4,
                "text": (
                    "The intervention improved test accuracy by "
                    "12 percent in the validation experiment."
                ),
            }],
        },
    )

    def fake_retrieve(query, chunks, top_k):
        assert chunks
        return [{**chunks[0], "retrieval_score": 2.75}]

    monkeypatch.setattr(service, "retrieve_evidence", fake_retrieve)

    result = service.prepare_research_evidence(_base_request())

    assert result.citation_match_status == "RESOLVED"
    assert result.retrieval_status.value == "full_text_available"
    assert result.evidence_count == 1
    evidence = result.verification_request.evidence[0]
    assert evidence.evidence_id
    assert evidence.source_id == paper["doi"]
    assert evidence.source_title == paper["title"]
    assert evidence.page_number == 4
    assert evidence.source_type.value == "full_text"
    assert evidence.retrieval_score == 2.75
    assert result.verification_request.citation_ids == ["[1]"]


def test_uses_abstract_when_open_access_pdf_is_unavailable(monkeypatch):
    paper = {
        "title": "A Study of Model Accuracy",
        "doi": "10.1234/example.001",
        "publication_year": 2024,
        "authors": ["A. Researcher"],
        "abstract": (
            "The intervention improved test accuracy by 12 percent "
            "in an experimental validation study."
        ),
        "pdf_url": None,
        "sources": ["semantic_scholar"],
    }
    monkeypatch.setattr(
        service,
        "search_academic_papers",
        lambda **kwargs: {
            "status": "SUCCESS",
            "papers": [paper],
            "source_status": {"semantic_scholar": {"status": "SUCCESS"}},
        },
    )

    def fake_retrieve(query, chunks, top_k):
        assert chunks[0]["evidence_kind"] == "abstract"
        return [{**chunks[0], "retrieval_score": 1.25}]

    monkeypatch.setattr(service, "retrieve_evidence", fake_retrieve)

    result = service.prepare_research_evidence(_base_request())

    assert result.retrieval_status.value == "resolved"
    evidence = result.verification_request.evidence[0]
    assert evidence.source_type.value == "abstract"
    assert evidence.page_number is None
    assert evidence.section_name == "Abstract"
    assert any("Only the abstract" in item for item in result.source_limitations)


def test_missing_citation_match_does_not_use_unmatched_papers(monkeypatch):
    monkeypatch.setattr(
        service,
        "search_academic_papers",
        lambda **kwargs: {
            "status": "SUCCESS",
            "papers": [{
                "title": "A Different Paper",
                "doi": "10.1234/different",
                "authors": [],
            }],
            "source_status": {"openalex": {"status": "SUCCESS"}},
        },
    )

    def should_not_download(*args, **kwargs):
        raise AssertionError("An unmatched paper must not be downloaded.")

    monkeypatch.setattr(service, "download_paper", should_not_download)

    result = service.prepare_research_evidence(_base_request())

    assert result.citation_match_status == "NOT FOUND"
    assert result.retrieval_status.value == "not_found"
    assert result.evidence_count == 0
    assert result.verification_request.evidence == []
