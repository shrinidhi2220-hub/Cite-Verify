# CiteVerify integrated backend: Members 1, 2 and 3

This backend package combines:

- **Member 1:** PDF/DOCX upload, text extraction, citation-marker extraction and DOI extraction.
- **Member 2:** OpenAlex, Semantic Scholar and Crossref search; paper matching; open-access PDF download; page extraction; chunking; BM25 evidence retrieval.
- **Member 3:** evidence-quality checks, Gemini passage assessment, numerical comparison, deterministic verdict generation and asynchronous verification jobs.

## 1. Install dependencies

From the repository root (the folder containing `backend/`):

```powershell
python -m pip install -r backend\requirements.txt
```

Keep your existing `.env` in the repository root. It should contain your Gemini configuration, for example:

```text
GEMINI_API_KEY=your_existing_key
GEMINI_MODEL=gemini-3.8-flash
```

Optional research API keys can be configured as `OPENALEX_API_KEY` and `SEMANTIC_SCHOLAR_API_KEY`. The clients are written to work without them where the providers allow unauthenticated access.

## 2. Start the API

```powershell
uvicorn backend.app.main:app
```

Open `http://127.0.0.1:8000/docs`.

## 3. Upload a paper/document (Member 1)

Use `POST /api/v1/documents/upload` with a PDF or DOCX file as multipart form data.

The response contains:

- `text`: extracted document text
- `citations`: numbered and author-year citation markers found in the text
- `dois`: DOI strings found in the text

**Important limitation:** Member 1 currently extracts citation markers and DOI strings; it does not yet turn every marker (for example `[1]`) into a complete bibliography record. Use the actual DOI or title from the document's reference list in the next step. A marker such as `[1]` alone is not sufficient to identify a paper.

## 4. Prepare evidence (Members 2 → 3 adapter)

Call `POST /api/v1/research/prepare` with a claim and a cited-paper query, title or DOI. Example:

```json
{
  "claim_id": "claim-001",
  "claim_text": "The intervention improved test accuracy by 12 percent.",
  "citation_title": "A Study of Model Accuracy",
  "citation_doi": "10.1234/example.001",
  "citation_ids": ["[1]"],
  "claim_type": "numerical",
  "per_page": 5,
  "top_k": 5,
  "max_papers": 3
}
```

The endpoint searches the academic providers, attempts to match the supplied citation, downloads an openly accessible PDF where a URL is available, extracts pages, chunks the text, ranks chunks with BM25, and converts the selected passages into Member 3's `VerificationRequest` shape.

The response includes a `verification_request` object and source limitations. If only an abstract is available, it is marked as `abstract`. If only metadata is available, it is marked as `metadata_only` and is not treated as proof.

## 5. Run verification (Member 3)

Copy the **entire `verification_request` object** from the preparation response and submit it to `POST /api/v1/verification/run`.

The endpoint returns HTTP 202 and a `job_id`. Poll:

`GET /api/v1/verification/status/{job_id}`

until `status` is `completed` or `failed`.

## 6. Important integration boundaries

- Topic-search results without a supplied DOI/title are explicitly marked as candidate literature; they are not claimed to be an exact citation match.
- A citation is not considered resolved unless the DOI or title matcher resolves it.
- Search metadata is not evidence. Full-text and abstract passages are distinguished in the verification request.
- The current job store is in-memory. Jobs are lost if the server process restarts; use one Uvicorn process for this prototype.
- `POST /api/v1/research/prepare` prepares evidence; it does not itself call Gemini. The returned `verification_request` is submitted to the existing verification endpoint.
- Uploaded demonstration data should not be represented as a real-world scientific finding. Final academic claims remain subject to human review.

## 7. One-call workflow for the frontend (recommended)

For Member 4, the simplest UI integration is to call:

`POST /api/v1/verification/run-from-research`

Example request:

```json
{
  "claim_id": "claim-001",
  "claim_text": "The intervention improved test accuracy by 12 percent.",
  "citation_title": "A Study of Model Accuracy",
  "citation_doi": "10.1234/example.001",
  "citation_ids": ["[1]"],
  "claim_type": "numerical",
  "per_page": 5,
  "top_k": 5,
  "max_papers": 3
}
```

This endpoint queues the full process: academic search → citation matching → open-access PDF retrieval → page extraction → chunking → BM25 ranking → Member 3 verification. It immediately returns a job ID. Poll the same status endpoint:

`GET /api/v1/verification/status/{job_id}`

The completed status contains both `result` (the final verdict) and `research_summary` (paper matching, retrieval and evidence counts/limitations). This avoids the frontend needing to copy the intermediate `verification_request` from `/research/prepare` into a second POST.

Use `/api/v1/research/prepare` only when the UI needs to preview retrieved evidence before triggering Gemini.
