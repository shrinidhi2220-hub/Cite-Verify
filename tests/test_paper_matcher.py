
import unittest

from backend.app.retrieval.paper_matcher import match_paper


class PaperMatcherTests(unittest.TestCase):

    def test_exact_doi_match(self):
        """DOI URL and plain DOI should match."""

        citation = {
            "doi": "https://doi.org/10.1167/tvst.9.2.42",
            "title": "A Review of Deep Learning for Glaucoma"
        }

        papers = [{
            "doi": "10.1167/tvst.9.2.42",
            "title": "A Review of Deep Learning for Glaucoma",
            "authors": ["Test Author"],
            "publication_year": 2020
        }]

        result = match_paper(citation, papers)

        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["confidence"], 1.0)

    def test_conflicting_doi_is_not_matched(self):
        """A different DOI must not be accepted as the same paper."""

        citation = {
            "doi": "10.1167/tvst.9.2.42",
            "title": "A Review of Deep Learning for Glaucoma"
        }

        papers = [{
            "doi": "10.9999/different-paper",
            "title": "A Review of Deep Learning for Glaucoma"
        }]

        result = match_paper(citation, papers)

        self.assertEqual(result["status"], "NOT FOUND")
        self.assertIsNone(result["matched_paper"])

    def test_title_fallback_when_paper_has_no_doi(self):
        """Use title matching when retrieved metadata has no DOI."""

        citation = {
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani"],
            "publication_year": 2017
        }

        papers = [{
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani"],
            "publication_year": 2017,
            "doi": None
        }]

        result = match_paper(citation, papers)

        self.assertEqual(result["status"], "RESOLVED")


if __name__ == "__main__":
    unittest.main()
