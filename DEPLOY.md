# Deploy (public free stack)

This app is set up for a **public URL** on free tiers:

| Piece | Free service | Why |
| --- | --- | --- |
| App (UI + API) | [Render](https://render.com) Free Web Service | One public HTTPS URL |
| Database | [Neon](https://neon.tech) Free Postgres | Persists sessions + created tables |
| AI | [Groq](https://console.groq.com) free key | Explanations (optional but wired) |

Databricks Apps cannot be public/anonymous, so this is the path for a shareable demo link.

## 1. Create a free Neon database

1. Sign up at https://console.neon.tech
2. Create a project
3. Copy the connection string (`postgresql://...`)

## 2. Deploy on Render

1. Push this repo to GitHub
2. Go to https://dashboard.render.com → **New** → **Blueprint**
3. Connect the repo (uses `render.yaml`)
4. Set secret env vars:
   - `GROQ_API_KEY` = your Groq key
   - `DATABASE_URL` = Neon connection string
5. Deploy

Your public URL will look like:

`https://import-confidence-check.onrender.com`

Anyone with the link can use it (no login).

### Notes

- Free Render services **sleep after idle**; first request can take ~30–60s to wake.
- Without `DATABASE_URL`, the app still runs on local SQLite inside the container (data is lost on redeploy). Neon keeps data across restarts.

## 3. Local production-like check

```bash
# build frontend static export
cd frontend
set NEXT_PUBLIC_API_BASE=
npm run build

# run API serving ./frontend/out
cd ../backend
set STATIC_DIR=../frontend/out
uvicorn app.main:app --port 8001
```

Open http://127.0.0.1:8001

## Env reference

```
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
AI_EXPLANATIONS_ENABLED=true
DATABASE_URL=postgresql://...
STATIC_DIR=/app/static
CORS_ORIGINS=*
```
