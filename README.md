# Import Confidence Check

Concept prototype for a Databricks PM take-home: detect silent type-inference damage during file upload.

## Architecture

- **Frontend:** Next.js (React) — Databricks-inspired UI (static export in production)
- **Backend:** FastAPI — parse, infer, scan, create-table session, optional Groq explanations
- **Database:** SQLite locally by default; Postgres via `DATABASE_URL` (Neon) in production

See [ARCHITECTURE.md](ARCHITECTURE.md) for full decisions. See [DEPLOY.md](DEPLOY.md) for a **public free** deploy (Render + Neon + Groq).

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

The product works fully without Groq.

## Demo script (2 minutes)

1. Open Add data.
2. Click **Create or modify table**.
3. Under Try a sample file, choose **Risks after preview row 50**.
4. Note the grid shows 50 clean rows.
5. Point to Import Confidence Check — risks found after row 50.
6. Open a leading-zero warning; show original `000123` → proposed `123`.
7. Explain joins / postal codes can break.
8. Click **Keep as String**.
9. Watch the risk clear / count drop.
10. Create the table.
11. Open Sample Data and confirm leading zeros preserved.

## Tests

```bash
cd backend
.\.venv\Scripts\python -m pytest tests -q
```

## Hosting

- Local: best for interview prep
- **Public demo (free):** Render + Neon + Groq — see [DEPLOY.md](DEPLOY.md)
- Databricks Apps: possible for org users only (not anonymous/public)
