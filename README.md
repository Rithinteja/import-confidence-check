# Import Confidence Check

Concept prototype for a Databricks PM take-home: catch silent type-inference damage during file upload.

## Architecture

- **Frontend:** Next.js (React), Databricks-inspired UI (static export in production)
- **Backend:** FastAPI for parse, infer, scan, create-table session, and optional Groq explanations
- **Database:** SQLite locally by default; Postgres via `DATABASE_URL` (Neon) in production

See [ARCHITECTURE.md](ARCHITECTURE.md) for decisions. See [DEPLOY.md](DEPLOY.md) for a public free deploy (Render + Neon + Groq).

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend
copy ..\.env.example .env.local   # or set NEXT_PUBLIC_API_BASE
npm install
npm run dev
```

App: http://127.0.0.1:3000

### Optional Groq

Set in repo-root `.env` or environment:

```
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
AI_EXPLANATIONS_ENABLED=true
```

The product works without Groq.

## Demo script (2 minutes)

1. Open the site Home page, then go to Data Ingestion → **Create or modify table**.
2. Under Try a sample file, choose **Leading-zero and conversion risks**.
3. Point to Import Confidence Check: leading zeros, dates, and rounding risks.
4. Open a leading-zero warning; show original `000123` → proposed `123`.
5. Explain joins / postal codes can break.
6. Click **Keep as String**.
7. Watch the risk clear / count drop.
8. Create the table.
9. Open Sample Data and confirm leading zeros preserved.

## Tests

```bash
cd backend
.\.venv\Scripts\python -m pytest tests -q
```

## Hosting

- Local: best for interview prep
- **Public demo (free):** Render + Neon + Groq. See [DEPLOY.md](DEPLOY.md).
- Databricks Apps: org users only (not anonymous/public)
