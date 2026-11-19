CITEVERIFY MERGED BACKEND PACKAGE

This ZIP contains a complete `backend/` folder, designed to be extracted into
D:\Hackathon\Cite-Verify (the repository root containing the existing backend folder).

Before replacing files, make a quick backup of your existing backend folder.

After extraction, from the repository root run:

    python -m pip install -r backend\requirements.txt
    python -m pytest backend\tests -v
    uvicorn backend.app.main:app

Swagger:
    http://127.0.0.1:8000/docs

New endpoints:
    POST /api/v1/documents/upload
    POST /api/v1/research/prepare
    POST /api/v1/verification/run-from-research
    GET  /api/v1/verification/status/{job_id}

Recommended one-call flow for the frontend:
    1. Upload PDF/DOCX to /api/v1/documents/upload.
    2. The user provides/selects a claim and a reference title or DOI.
    3. Call /api/v1/verification/run-from-research.
    4. Poll /api/v1/verification/status/{job_id}.

The uploaded document endpoint extracts citation markers and DOI strings, but
it does not yet map every marker such as [1] to a full bibliography record.
The request to run-from-research therefore needs a citation_title or
citation_doi (or a search_query for explicitly topical candidate research).

The existing .env is not included. Keep your current Gemini API key in the
repository-root .env file and never commit that file.
