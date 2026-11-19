"""Extract text from PDF documents."""

import fitz


def extract_text(pdf_path: str) -> str:
    """Return text from every page in the PDF at ``pdf_path``."""
    extracted_pages = []

    # Open the PDF and collect the text from each page in order.
    with fitz.open(pdf_path) as pdf_document:
        for page in pdf_document:
            extracted_pages.append(page.get_text())

    # Separate page text with a newline so page boundaries remain readable.
    return "\n".join(extracted_pages)
