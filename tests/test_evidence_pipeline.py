
import unittest
from unittest.mock import patch

from backend.app.retrieval.evidence_pipeline import retrieve_claim_evidence


class EvidencePipelineTests(unittest.TestCase):

    def setUp(self):
        self.paper = {
            "openalex_id": "https://openalex.org/W123",
            "title": "Attention Mechanisms in Neural Networks",
            "doi": "10.1234/test",
            "publication_year": 2024,
            "authors": ["Test Author"],
            "sources": ["openalex"],
            "pdf_url": "https://example.org/paper.pdf",
            "landing_page_url": "https://example.org/paper"
        }

        self.chunk = {
            "chunk_id": "W123_chunk_1",
            "paper_id": "W123",
            "page_number": 2,
            "text": "Attention mechanisms improve neural network processing.",
            "word_count": 7
        }

        self.search_result = {
            "status": "SUCCESS",
            "papers": [self.paper],
            "source_status": {
                "openalex": {"status": "SUCCESS", "results": 1},
                "semantic_scholar": {"status": "SUCCESS", "results": 0}
            }
        }

    def test_complete_pipeline(self):
        """Test the complete retrieval sequence."""

        with (
            patch(
                "backend.app.retrieval.evidence_pipeline.search_academic_papers",
                return_value=self.search_result
            ),
            patch(
                "backend.app.retrieval.evidence_pipeline.download_paper",
                return_value={
                    "status": "FULL TEXT AVAILABLE",
                    "file_path": "test.pdf",
                    "reason": "Download successful."
                }
            ) as downloader,
            patch(
                "backend.app.retrieval.evidence_pipeline.extract_pdf_text",
                return_value={
                    "status": "SUCCESS",
                    "pages": [{"page_number": 2, "text": self.chunk["text"]}],
                    "total_pages": 3,
                    "extracted_pages": 1
                }
            ),
            patch(
                "backend.app.retrieval.evidence_pipeline.chunk_paper_text",
                return_value=[self.chunk.copy()]
            ),
            patch(
                "backend.app.retrieval.evidence_pipeline.retrieve_evidence",
                return_value=[{
                    **self.chunk,
                    "retrieval_score": 3.5,
                    "matched_terms": ["attention"]
                }]
            )
        ):
            result = retrieve_claim_evidence("attention mechanisms")

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["total_chunks"], 1)
        self.assertEqual(result["retrieved_evidence_count"], 1)
        self.assertEqual(
            result["retrieved_evidence"][0]["page_number"], 2
        )
        downloader.assert_called_once()

    def test_metadata_only_fallback(self):
        """Test a paper that has metadata but no PDF URL."""

        metadata_only_paper = {
            **self.paper,
            "pdf_url": None
        }

        search_result = {
            **self.search_result,
            "papers": [metadata_only_paper]
        }

        with (
            patch(
                "backend.app.retrieval.evidence_pipeline.search_academic_papers",
                return_value=search_result
            ),
            patch(
                "backend.app.retrieval.evidence_pipeline.download_paper"
            ) as downloader
        ):
            result = retrieve_claim_evidence("attention mechanisms")

        self.assertEqual(
            result["papers_processed"][0]["status"],
            "METADATA ONLY"
        )
        self.assertEqual(result["retrieved_evidence_count"], 0)
        self.assertEqual(result["total_chunks"], 0)
        downloader.assert_not_called()

    def test_partial_search_status_is_preserved(self):
        """Test that a failed search provider produces PARTIAL status."""

        partial_result = {
            **self.search_result,
            "status": "PARTIAL"
        }

        with (
            patch(
                "backend.app.retrieval.evidence_pipeline.search_academic_papers",
                return_value=partial_result
            ),
            patch(
                "backend.app.retrieval.evidence_pipeline.download_paper",
                return_value={
                    "status": "FULL TEXT AVAILABLE",
                    "file_path": "test.pdf",
                    "reason": "Download successful."
                }
            ),
            patch(
                "backend.app.retrieval.evidence_pipeline.extract_pdf_text",
                return_value={
                    "status": "SUCCESS",
                    "pages": [{"page_number": 2, "text": self.chunk["text"]}],
                    "total_pages": 3,
                    "extracted_pages": 1
                }
            ),
            patch(
                "backend.app.retrieval.evidence_pipeline.chunk_paper_text",
                return_value=[self.chunk.copy()]
            ),
            patch(
                "backend.app.retrieval.evidence_pipeline.retrieve_evidence",
                return_value=[{
                    **self.chunk,
                    "retrieval_score": 3.5,
                    "matched_terms": ["attention"]
                }]
            )
        ):
            result = retrieve_claim_evidence("attention mechanisms")

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["retrieved_evidence_count"], 1)

    def test_no_papers_found(self):
        """Test unavailable search services without inventing evidence."""

        with patch(
            "backend.app.retrieval.evidence_pipeline.search_academic_papers",
            return_value={
                "status": "UNAVAILABLE",
                "papers": [],
                "source_status": {
                    "openalex": {"status": "UNAVAILABLE"},
                    "semantic_scholar": {"status": "UNAVAILABLE"}
                }
            }
        ):
            result = retrieve_claim_evidence("attention mechanisms")

        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["total_chunks"], 0)
        self.assertEqual(result["retrieved_evidence_count"], 0)
        self.assertEqual(result["retrieved_evidence"], [])


if __name__ == "__main__":
    unittest.main()
