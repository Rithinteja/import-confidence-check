# Architecture

## Summary

| Layer | Choice |
|---|---|
| Frontend | Next.js App Router + TypeScript |
| Backend | **FastAPI (Python)** |
| Scanner | Deterministic Python rules in `backend/app/scanner/` |
| AI | Optional Groq via FastAPI only |
| Storage | In-memory sessions (no DB) |

## Answers

1. **Frontend stack:** Next.js + React + TypeScript + custom CSS (Databricks visual tokens).
2. **Backend stack:** FastAPI + Uvicorn + Pydantic + openpyxl + httpx.
3. **Browser work:** Rendering, navigation, calling APIs, local UI state (drawers, toggles).
4. **Server work:** File parse, type inference, full-file scan, schema fixes, table materialization, Groq proxy.
5. **Raw values:** Parsed into `list[list[str]]` and never mutated. Conversion runs on copies.
6. **Parsing:** CSV/TSV via stdlib `csv`; JSON via `json` (quoted strings stay strings); Excel via openpyxl `data_only`.
7. **Comparison:** For each cell, `convert_value(original, proposed_type)` then compare meaning (leading zeros, Decimal equality, nulls, collisions).
8. **Large files:** Soft 10MB limit; scan is synchronous on server for prototype scale; UI shows loading while request runs. Preview always first 50 rows.
9. **Local run:** `uvicorn` on :8000 + `next dev` on :3000.
10. **Databricks App?** Yes, FastAPI is a first-class Databricks Apps pattern. Include `app.yaml` with `uvicorn` listening on `DATABRICKS_APP_PORT`. Serve built frontend as static files from FastAPI or run a Node start command — for interview, local/Vercel is enough.
11. **Databricks hosting changes:** Bundle frontend build into app, set secrets via Apps env, bind `0.0.0.0:$DATABRICKS_APP_PORT`, no localhost CORS.
12. **Easier public host for interview:** Frontend on Vercel + backend on Render/Railway/Fly. Fastest path for a reviewer link.
13. **Does Groq add value?** Yes for plain-language explanations and Q&A — not for detection.
14. **Always deterministic:** risk categories, counts, original/converted examples, recommended types, outside-preview flags.
15. **Security/privacy:** No persistent file storage; no raw logs of cell values; Groq gets masked structured summaries only; API key server-side; validate extensions; size limit; app labeled concept prototype.

## Why FastAPI (not Next-only)

- Matches Databricks Apps Python runtime well.
- Keeps conversion logic testable with pytest independent of UI.
- Central place for Groq secrets.
- Clear upload boundary for privacy documentation.

## Groq design

- Routes: `/api/groq/explain-risk`, `/api/groq/import-summary`, `/api/groq/ask`
- Default model: `openai/gpt-oss-120b` (configurable; Llama 3.3 70B shut down Aug 16 2026)
- If key missing/timeout: return deterministic fallback copy; never block create-table
- Groq cannot change scanner outputs

## Data flow

Upload → parse raw strings → infer schema → scan all rows → UI panel → apply fix → rescan → create table (materialize with final types) → catalog view
