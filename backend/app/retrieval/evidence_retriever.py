
import re
from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    """
    Convert text into lowercase tokens for BM25 retrieval.
    """

    return re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())


def retrieve_evidence(
    query: str,
    chunks: list[dict],
    top_k: int = 5
) -> list[dict]:
    """
    Retrieve and rank the most relevant evidence chunks for a claim.

    Uses BM25 keyword-based ranking.

    Returns the original chunk metadata along with its
    retrieval score and matched query terms.
    """

    # Validate inputs
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query cannot be empty.")

    if not isinstance(chunks, list):
        raise ValueError("Chunks must be provided as a list.")

    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        raise ValueError("top_k must be a positive integer.")

    query_tokens = tokenize(query)

    if not query_tokens:
        raise ValueError("Query contains no searchable words.")

    if not chunks:
        return []

    valid_chunks = []
    tokenized_corpus = []

    # Prepare paper chunks for BM25
    for chunk in chunks:

        if not isinstance(chunk, dict):
            raise ValueError("Each chunk must be a dictionary.")

        text = chunk.get("text", "")
        chunk_id = chunk.get("chunk_id")
        paper_id = chunk.get("paper_id")
        page_number = chunk.get("page_number")

        if not isinstance(text, str) or not text.strip():
            continue

        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError("Every chunk must have a valid chunk_id.")

        if not isinstance(paper_id, str) or not paper_id.strip():
            raise ValueError("Every chunk must have a valid paper_id.")

        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number < 1
        ):
            raise ValueError("Every chunk must have a valid page_number.")

        tokens = tokenize(text)

        if not tokens:
            continue

        valid_chunks.append(chunk)
        tokenized_corpus.append(tokens)

    if not valid_chunks:
        return []

    # Build the BM25 index
    bm25 = BM25Okapi(tokenized_corpus)

    # Calculate relevance scores
    scores = bm25.get_scores(query_tokens)

    ranked_evidence = []

    for index, score in enumerate(scores):
        if score <= 0:
            continue

        chunk = valid_chunks[index]
        document_tokens = set(tokenized_corpus[index])

        matched_terms = sorted(
            set(query_tokens).intersection(document_tokens)
        )

        # Ignore chunks with no matching query terms
        if not matched_terms:
            continue

        ranked_evidence.append({
            **chunk,
            "retrieval_score": round(float(score), 4),
            "matched_terms": matched_terms
        })

    # Highest-scoring passages first
    ranked_evidence.sort(
        key=lambda item: item["retrieval_score"],
        reverse=True
    )

    return ranked_evidence[:top_k]
