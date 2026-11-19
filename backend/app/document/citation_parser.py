"""Find common citation formats and DOI values in document text."""

import re
from typing import List


def extract_numbered_citations(text: str) -> List[str]:
    """Return bracketed numeric citations such as [1] and [15]."""
    # Match one or more digits surrounded by square brackets.
    return re.findall(r"\[\d+\]", text)


def extract_author_year_citations(text: str) -> List[str]:
    """Return author-year citations such as (Smith, 2023)."""
    # Match a single-word author name followed by a four-digit year.
    return re.findall(r"\([A-Z][A-Za-z'-]*,\s*\d{4}\)", text)


def extract_dois(text: str) -> List[str]:
    """Return DOI values found in the text."""
    # DOI values begin with 10., followed by a registrant number and a suffix.
    doi_pattern = r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+"
    dois = re.findall(doi_pattern, text, flags=re.IGNORECASE)

    # Remove punctuation that commonly follows a DOI in a sentence.
    return [doi.rstrip(".,;:") for doi in dois]
