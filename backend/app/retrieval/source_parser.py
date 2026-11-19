
from pathlib import Path
import pymupdf


def extract_pdf_text(pdf_path: str) -> dict:
    """
    Extract text from a PDF page by page.

    Preserves original page numbers and returns structured text.
    """

    path = Path(pdf_path)

    if not path.exists():
        return {
            "status": "NOT FOUND",
            "pages": [],
            "reason": "PDF file does not exist."
        }

    if path.suffix.lower() != ".pdf":
        return {
            "status": "INVALID FILE",
            "pages": [],
            "reason": "File must have a PDF extension."
        }

    pages = []

    try:
        with pymupdf.open(path) as document:

            if document.is_encrypted:
                return {
                    "status": "UNAVAILABLE",
                    "pages": [],
                    "reason": "PDF is password protected."
                }

            # Get total page count before processing.
            total_pages = document.page_count

            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text").strip()

                if text:
                    pages.append({
                        "page_number": page_number,
                        "text": text
                    })

        if not pages:
            return {
                "status": "NO TEXT",
                "pages": [],
                "total_pages": total_pages,
                "extracted_pages": 0,
                "reason": "No extractable text found. PDF may be scanned."
            }

        return {
            "status": "SUCCESS",
            "pages": pages,
            "total_pages": total_pages,
            "extracted_pages": len(pages),
            "reason": "PDF text extracted successfully."
        }

    except (pymupdf.FileDataError, OSError):
        return {
            "status": "INVALID FILE",
            "pages": [],
            "reason": "Could not read the PDF file."
        }
