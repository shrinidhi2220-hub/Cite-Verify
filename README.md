# CiteVerify

CiteVerify is an evidence-first scientific citation review MVP. It accepts PDF files, extracts selectable text, identifies possible claims and citations, and produces a report that states when claims cannot be verified.

## Run locally

Use two terminals from the repository root.

Backend:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Frontend:

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Open the Vite URL printed in the frontend terminal (normally `http://localhost:5173`). The frontend sends `/api` requests through Vite's proxy to `http://127.0.0.1:4000`, so it works from localhost or the displayed network URL without hardcoding the browser's host. For production, set `VITE_API_URL` if the API is not served under the same origin and configure `FRONTEND_URL` on the API.

Set a unique `JWT_SECRET` in `.env` before sharing or deploying the server. `DATA_DIR` and `UPLOAD_DIR` default to repository-local `data/` and `uploads/`.

## Current verification limitations

The current engine is extraction-only. It uses simple text patterns to identify possible claims and in-text citations. It does not retrieve cited papers, compare source evidence, or determine that a claim is supported, contradicted, or unsupported. Results therefore remain `UNVERIFIABLE`. Scanned PDFs without selectable text are not OCR-processed. Do not treat reports as scientific verification.

## Checks

```powershell
npm test
cd frontend
npm run build
npm run lint
```
