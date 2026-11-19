
import re


def chunk_paper_text(
    pages: list[dict],
    paper_id: str,
    chunk_size: int = 150,
    overlap: int = 30
) -> list[dict]:
    """
    Split extracted paper text into smaller overlapping chunks.

    Each chunk preserves its paper ID and original page number.
    """

    if not isinstance(pages, list):
        raise ValueError("pages must be a list.")

    if not isinstance(paper_id, str) or not paper_id.strip():
        raise ValueError("paper_id cannot be empty.")

    if (
        not isinstance(chunk_size, int)
        or isinstance(chunk_size, bool)
        or chunk_size <= 0
    ):
        raise ValueError("chunk_size must be a positive integer.")

    if (
        not isinstance(overlap, int)
        or isinstance(overlap, bool)
        or overlap < 0
        or overlap >= chunk_size
    ):
        raise ValueError(
            "overlap must be between 0 and chunk_size - 1."
        )

    safe_paper_id = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        paper_id.strip()
    )

    chunks = []
    chunk_number = 1

    for page in pages:

        if not isinstance(page, dict):
            continue

        page_number = page.get("page_number")
        text = page.get("text", "")

        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number < 1
        ):
            continue

        if not isinstance(text, str) or not text.strip():
            continue

        words = text.split()
        start = 0

        while start < len(words):

            end = start + chunk_size
            chunk_words = words[start:end]

            chunks.append({
                "chunk_id": f"{safe_paper_id}_chunk_{chunk_number}",
                "paper_id": paper_id.strip(),
                "page_number": page_number,
                "text": " ".join(chunk_words),
                "word_count": len(chunk_words)
            })

            chunk_number += 1

            if end >= len(words):
                break

            start = end - overlap

    return chunks
