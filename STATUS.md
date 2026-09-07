# Implemented checklist

## P0
- [x] Databricks-inspired end-to-end UI
- [x] Working CSV, JSON, Excel upload (FastAPI)
- [x] File parsing with raw string preservation
- [x] Schema inference
- [x] Source-versus-converted comparison
- [x] Leading-zero detection
- [x] Identifier-collision detection
- [x] Precision / decimal-scale loss detection
- [x] Null-after-conversion + invalid date/timestamp
- [x] Full-file scan; preview capped at 50
- [x] Risk panel + affected-row details
- [x] One-click schema fixes + rescan
- [x] Create-table confirmation + Catalog result page
- [x] FastAPI backend
- [x] Optional Groq explanations (fallback without key)

## P1
- [x] Sample-file gallery
- [x] Affected-row counts for full file
- [ ] Saved import profile in localStorage
- [ ] Downloadable risk report
- [x] Loading / error states

## P2
- [ ] Workspace-wide import rules
- [ ] Databricks-native production deploy beyond app.yaml scaffold
- [x] Groq ask / summary / explain endpoints (optional)

## Known limitations
- Excel leading zeros may already be lost inside Excel before upload
- Inference heuristics approximate Databricks, not identical
- Sessions are in-memory only (lost on server restart)
- No Playwright suite checked into CI yet (unit tests cover scanner)
