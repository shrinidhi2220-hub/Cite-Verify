"""Upload documents and return their text, citations, and DOIs."""

import os
import tempfile
from typing import Dict

from fastapi import APIRouter, File, HTTPException, UploadFile

from .citation_parser import (
    extract_author_year_citations,
    extract_dois,
    extract_numbered_citations,
)
from .docx_parser import extract_text as extract_docx_text
from .pdf_parser import extract_text as extract_pdf_text

router = APIRouter()


@router.post("/upload")
def upload_document(file: UploadFile = File(...)) -> Dict[str, object]:
    """Extract content from an uploaded PDF or DOCX document."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    # Choose the right parser based on the uploaded file's extension.
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension == ".pdf":
        text_parser = extract_pdf_text
    elif file_extension == ".docx":
        text_parser = extract_docx_text
    else:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported.",
        )

    # Save the upload temporarily because the document parsers accept file paths.
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = os.path.join(
            temporary_directory,
            "uploaded" + file_extension,
        )
        with open(temporary_path, "wb") as temporary_file:
            temporary_file.write(file.file.read())

        text = text_parser(temporary_path)

    # Combine both supported citation styles into one list.
    citations = extract_numbered_citations(text)
    citations.extend(extract_author_year_citations(text))

    return {
        "filename": file.filename,
        "text": text,
        "citations": citations,
        "dois": extract_dois(text),
    }
