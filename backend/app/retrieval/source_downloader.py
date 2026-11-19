
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx


DOWNLOAD_DIR = Path("data/papers")
MAX_FILE_SIZE = 30 * 1024 * 1024  # 30 MB


def download_paper(pdf_url: str, paper_id: str) -> dict:
    """
    Download an openly accessible PDF paper.

    Returns download status and the saved file path.
    """

    if not pdf_url or not pdf_url.strip():
        return {
            "status": "UNAVAILABLE",
            "file_path": None,
            "reason": "No PDF URL provided."
        }

    if not paper_id or not paper_id.strip():
        raise ValueError("paper_id cannot be empty.")

    parsed_url = urlparse(pdf_url)

    if parsed_url.scheme != "https" or not parsed_url.netloc:
        return {
            "status": "UNAVAILABLE",
            "file_path": None,
            "reason": "Only valid HTTPS PDF URLs are accepted."
        }

    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", paper_id)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DOWNLOAD_DIR / f"{safe_id}.pdf"

    try:
        with httpx.stream(
            "GET",
            pdf_url,
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "CiteVerify/0.1"}
        ) as response:

            response.raise_for_status()

            content_type = response.headers.get(
                "content-type", ""
            ).lower()

            if "application/pdf" not in content_type:
                return {
                    "status": "UNAVAILABLE",
                    "file_path": None,
                    "reason": "The URL did not return a PDF."
                }

            total_size = 0

            with file_path.open("wb") as file:
                for chunk in response.iter_bytes():
                    total_size += len(chunk)

                    if total_size > MAX_FILE_SIZE:
                        file.close()
                        file_path.unlink(missing_ok=True)

                        return {
                            "status": "UNAVAILABLE",
                            "file_path": None,
                            "reason": "PDF exceeds the 30 MB limit."
                        }

                    file.write(chunk)

        # Validate the PDF file signature.
        with file_path.open("rb") as file:
            signature = file.read(5)

        if signature != b"%PDF-":
            file_path.unlink(missing_ok=True)

            return {
                "status": "UNAVAILABLE",
                "file_path": None,
                "reason": "Downloaded file is not a valid PDF."
            }

        return {
            "status": "FULL TEXT AVAILABLE",
            "file_path": str(file_path),
            "reason": "PDF downloaded and validated successfully."
        }

    except httpx.HTTPStatusError as exc:
        file_path.unlink(missing_ok=True)

        return {
            "status": "UNAVAILABLE",
            "file_path": None,
            "reason": f"PDF server returned HTTP {exc.response.status_code}."
        }

    except httpx.RequestError:
        file_path.unlink(missing_ok=True)

        return {
            "status": "UNAVAILABLE",
            "file_path": None,
            "reason": "Could not connect to the PDF server."
        }

    except OSError:
        file_path.unlink(missing_ok=True)

        return {
            "status": "UNAVAILABLE",
            "file_path": None,
            "reason": "Could not save the PDF locally."
        }
