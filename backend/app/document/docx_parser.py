"""Extract text from DOCX documents."""

from docx import Document


def extract_text(docx_path: str) -> str:
    """Return paragraph text from the DOCX file at ``docx_path``."""
    document = Document(docx_path)

    # Keep paragraph text in document order and separate paragraphs with newlines.
    text = []
    for paragraph in document.paragraphs:
        text.append(paragraph.text)

    return "\n".join(text)