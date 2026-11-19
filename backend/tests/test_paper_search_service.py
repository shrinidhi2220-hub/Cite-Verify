from backend.app.retrieval import paper_search_service as service


def test_resolves_arxiv_doi_directly_without_semantic_scholar(monkeypatch):
    paper = {
        "arxiv_id": "1706.03762",
        "title": "Attention Is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "publication_year": 2017,
        "authors": ["Ashish Vaswani"],
        "abstract": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.",
        "pdf_url": "https://arxiv.org/pdf/1706.03762",
    }

    monkeypatch.setattr(service, "_arxiv_doi_is_resolved", lambda doi: paper)

    def should_not_be_called(*args, **kwargs):
        raise AssertionError("General search providers should not be required for an exact arXiv DOI.")

    monkeypatch.setattr(service, "search_works", should_not_be_called)
    monkeypatch.setattr(service, "search_papers", should_not_be_called)
    monkeypatch.setattr(service, "get_crossref_work_by_doi", should_not_be_called)

    result = service.search_academic_papers(
        query="Attention Is All You Need",
        doi="10.48550/arXiv.1706.03762",
    )

    assert result["status"] == "SUCCESS"
    assert len(result["papers"]) == 1
    assert result["papers"][0]["title"] == "Attention Is All You Need"
    assert result["papers"][0]["pdf_url"].endswith("/1706.03762")
    assert result["source_status"]["arxiv"]["status"] == "SUCCESS"


def test_arxiv_doi_parser_accepts_doi_url_and_version():
    from backend.app.retrieval.arxiv_client import extract_arxiv_id_from_doi

    assert extract_arxiv_id_from_doi(
        "https://doi.org/10.48550/arXiv.1706.03762"
    ) == "1706.03762"
    assert extract_arxiv_id_from_doi("10.48550/arxiv.1706.03762v2") == "1706.03762"
    assert extract_arxiv_id_from_doi("10.1234/example") is None


def test_non_arxiv_doi_falls_back_from_crossref_to_datacite(monkeypatch):
    monkeypatch.setattr(service, "_arxiv_doi_is_resolved", lambda doi: None)
    monkeypatch.setattr(service, "search_works", lambda query, per_page: [])
    monkeypatch.setattr(service, "search_papers", lambda query, limit: [])
    monkeypatch.setattr(service, "get_crossref_work_by_doi", lambda doi: None)

    datacite_paper = {
        "title": "A DataCite registered work",
        "doi": "10.9999/example",
        "authors": ["Researcher"],
        "abstract": "An abstract.",
    }
    monkeypatch.setattr(
        service,
        "get_datacite_work_by_doi",
        lambda doi: datacite_paper,
    )

    result = service.search_academic_papers(
        query="A DataCite registered work",
        doi="10.9999/example",
    )

    assert result["papers"][0]["title"] == "A DataCite registered work"
    assert "datacite" in result["papers"][0]["sources"]
    assert result["source_status"]["datacite"]["status"] == "SUCCESS"


def test_semantic_scholar_rate_limit_does_not_break_direct_arxiv_lookup(monkeypatch):
    paper = {
        "arxiv_id": "1706.03762",
        "title": "Attention Is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "publication_year": 2017,
        "authors": ["Ashish Vaswani"],
        "abstract": "Transformer abstract.",
        "pdf_url": "https://arxiv.org/pdf/1706.03762",
    }
    monkeypatch.setattr(service, "_arxiv_doi_is_resolved", lambda doi: paper)

    result = service.search_academic_papers(
        query="Attention Is All You Need",
        doi="10.48550/arXiv.1706.03762",
    )

    assert result["status"] == "SUCCESS"
    assert result["papers"]
    assert result["source_status"]["semantic_scholar"]["status"] == "SKIPPED"


def test_title_search_uses_crossref_to_discover_doi_when_reference_has_no_doi(monkeypatch):
    paper = {
        "title": "A Detailed Study of Benchmark Model Performance",
        "doi": "10.5555/benchmark.2021.001",
        "publication_year": 2021,
        "authors": ["J. Smith"],
        "url": "https://doi.org/10.5555/benchmark.2021.001",
        "pdf_url": None,
    }
    monkeypatch.setattr(service, "search_works", lambda query, per_page: [])
    monkeypatch.setattr(service, "search_papers", lambda query, limit: [])
    monkeypatch.setattr(service, "search_crossref_works", lambda query, rows: [paper])

    result = service.search_academic_papers(
        query="A Detailed Study of Benchmark Model Performance",
    )

    from backend.app.retrieval.paper_matcher import match_paper

    match = match_paper(
        {
            "title": "A Detailed Study of Benchmark Model Performance",
            "authors": ["J. Smith"],
            "publication_year": 2021,
        },
        result["papers"],
    )

    assert result["status"] == "SUCCESS"
    assert result["source_status"]["crossref_search"]["status"] == "SUCCESS"
    assert match["status"] == "RESOLVED"
    assert match["matched_paper"]["doi"] == "10.5555/benchmark.2021.001"


def test_crossref_bibliographic_search_normalizes_candidate_metadata(monkeypatch):
    from backend.app.retrieval import crossref_client

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "items": [{
                        "title": ["A Detailed Study of Benchmark Model Performance"],
                        "DOI": "10.5555/benchmark.2021.001",
                        "author": [{"given": "Jane", "family": "Smith"}],
                        "published-print": {"date-parts": [[2021, 4, 1]]},
                        "publisher": "Example Publisher",
                        "URL": "https://doi.org/10.5555/benchmark.2021.001",
                        "link": [],
                    }]
                }
            }

    captured = {}

    def fake_get(url, params, timeout, headers):
        captured.update({"url": url, "params": params, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(crossref_client.httpx, "get", fake_get)
    results = crossref_client.search_works("A Detailed Study of Benchmark Model Performance", rows=3)

    assert captured["params"]["query.bibliographic"] == "A Detailed Study of Benchmark Model Performance"
    assert captured["params"]["rows"] == 3
    assert results[0]["doi"] == "10.5555/benchmark.2021.001"
    assert results[0]["authors"] == ["Jane Smith"]
    assert results[0]["publication_year"] == 2021
