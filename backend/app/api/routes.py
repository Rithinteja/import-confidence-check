from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import FIXTURES_DIR, get_settings
from app.models import (
    ApplyFixRequest,
    CreateTableRequest,
    CreatedTableResponse,
    GroqAskRequest,
    GroqExplainRequest,
    GroqSummaryRequest,
    GroqTextResponse,
    ImportSessionResponse,
    RescanRequest,
    SampleFileInfo,
)
from app.scanner.engine import apply_recommended_fix
from app.services import groq_client
from app.services.parse import parse_bytes, parse_path
from app.session_store import store

router = APIRouter()

SAMPLES: list[SampleFileInfo] = [
    SampleFileInfo(
        id="after-preview",
        label="Risks after preview (75 rows)",
        filename="databricks_preview_50_row_limit_test.csv",
        description="Recommended first. Preview shows 50 clean rows; risks start at row 51+.",
    ),
    SampleFileInfo(
        id="leading-zero",
        label="Leading-zero and conversion risks",
        filename="conversion_edge_cases.csv",
        description="Customer IDs, postal codes, rounding, invalid dates",
    ),
    SampleFileInfo(
        id="excel",
        label="Excel import risks",
        filename="databricks_import_type_risks.xlsx",
        description="XLSX leading zeros, dates, and mixed values",
    ),
    SampleFileInfo(
        id="rounding",
        label="Numeric rounding test",
        filename="numeric_rounding_control.csv",
        description="Safe 20.23 vs risky 19.99 under decimal scale 0",
    ),
    SampleFileInfo(
        id="json",
        label="JSON type test",
        filename="numeric_string_control.json",
        description="Quoted identifiers vs numeric JSON values",
    ),
    SampleFileInfo(
        id="json-mixed",
        label="JSON mixed type risks",
        filename="databricks_mixed_type_risks.json",
        description="Invalid dates and mixed amounts in JSON",
    ),
    SampleFileInfo(
        id="clean",
        label="Clean import example",
        filename="clean_import_control.csv",
        description="Control file with no meaningful conversion risks",
    ),
]


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    from app.db import get_database_url

    url = get_database_url()
    backend = "postgres" if "postgresql" in url or "postgres" in url else "sqlite"
    return {
        "ok": True,
        "groq_configured": settings.groq_configured,
        "ai_enabled": settings.ai_explanations_enabled,
        "database": backend,
    }


@router.get("/samples", response_model=list[SampleFileInfo])
def list_samples() -> list[SampleFileInfo]:
    return SAMPLES


@router.get("/samples/{sample_id}/file")
def download_sample(sample_id: str) -> FileResponse:
    meta = next((s for s in SAMPLES if s.id == sample_id), None)
    if not meta:
        raise HTTPException(404, "Sample not found")
    path = FIXTURES_DIR / meta.filename
    if not path.exists():
        raise HTTPException(404, "Fixture missing")
    return FileResponse(
        path,
        filename=meta.filename,
        content_disposition_type="attachment",
    )


@router.post("/import/upload", response_model=ImportSessionResponse)
async def upload_file(file: UploadFile = File(...)) -> ImportSessionResponse:
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(400, "File exceeds 10MB limit")
    filename = file.filename or "upload.csv"
    try:
        parsed = parse_bytes(data, filename)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
    session = store.create(parsed)
    return store.response(session)


@router.post("/import/sample/{sample_id}", response_model=ImportSessionResponse)
def load_sample(sample_id: str) -> ImportSessionResponse:
    meta = next((s for s in SAMPLES if s.id == sample_id), None)
    if not meta:
        raise HTTPException(404, "Sample not found")
    path = FIXTURES_DIR / meta.filename
    if not path.exists():
        raise HTTPException(404, "Fixture missing")
    try:
        parsed = parse_path(path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc
    session = store.create(parsed)
    return store.response(session)


@router.get("/import/{session_id}", response_model=ImportSessionResponse)
def get_session(session_id: str) -> ImportSessionResponse:
    try:
        session = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(404, "Session not found") from exc
    return store.response(session)


@router.post("/import/{session_id}/rescan", response_model=ImportSessionResponse)
def rescan(session_id: str, body: RescanRequest) -> ImportSessionResponse:
    try:
        session = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(404, "Session not found") from exc
    # Preserve names order
    by_name = {c.name: c for c in body.columns}
    session.columns = [by_name.get(c.name, c) for c in session.columns]
    # Allow extra renamed? stick to existing headers
    session.rescan()
    store.persist(session)
    return store.response(session)


@router.post("/import/{session_id}/apply-fix", response_model=ImportSessionResponse)
def apply_fix(session_id: str, body: ApplyFixRequest) -> ImportSessionResponse:
    try:
        session = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(404, "Session not found") from exc
    risk = next((r for r in session.risks if r.risk_id == body.risk_id), None)
    if not risk:
        raise HTTPException(404, "Risk not found or already resolved")
    session.columns = apply_recommended_fix(session.columns, risk)
    before = {r.risk_id for r in session.risks}
    session.rescan()
    after = {r.risk_id for r in session.risks}
    if body.risk_id in before and body.risk_id not in after:
        store.bump_resolved(session_id)
    store.persist(session)
    return store.response(session)


@router.patch("/import/{session_id}/meta", response_model=ImportSessionResponse)
def update_meta(session_id: str, payload: dict) -> ImportSessionResponse:
    try:
        session = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(404, "Session not found") from exc
    if "table_name" in payload and payload["table_name"]:
        session.table_name = str(payload["table_name"])
    if "catalog" in payload and payload["catalog"]:
        session.catalog = str(payload["catalog"])
    if "schema" in payload and payload["schema"]:
        session.schema_name = str(payload["schema"])
    if "action" in payload and payload["action"]:
        session.action = str(payload["action"])
    store.persist(session)
    return store.response(session)


@router.post("/import/{session_id}/create", response_model=CreatedTableResponse)
def create_table(session_id: str, body: CreateTableRequest) -> CreatedTableResponse:
    try:
        session = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(404, "Session not found") from exc
    try:
        return store.create_table(session, force=body.force)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/tables")
def list_tables() -> list[dict]:
    return store.list_tables()


@router.get("/import/{session_id}/created", response_model=CreatedTableResponse)
def get_created(session_id: str) -> CreatedTableResponse:
    try:
        return store.get_created(session_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc) if str(exc) else "Table not found") from exc


@router.post("/groq/explain-risk", response_model=GroqTextResponse)
async def groq_explain(body: GroqExplainRequest) -> GroqTextResponse:
    return await groq_client.explain_risk(get_settings(), body.risk, body.column_role)


@router.post("/groq/import-summary", response_model=GroqTextResponse)
async def groq_summary(body: GroqSummaryRequest) -> GroqTextResponse:
    return await groq_client.import_summary(
        get_settings(),
        body.unresolved_risks,
        body.resolved_risks,
        body.total_rows,
        body.preview_limit,
    )


@router.post("/groq/ask", response_model=GroqTextResponse)
async def groq_ask(body: GroqAskRequest) -> GroqTextResponse:
    context = {
        "risk_categories": body.risk_categories,
        "column_roles": body.column_roles,
        "affected_row_counts": body.affected_row_counts,
        "masked_examples": body.masked_examples,
        "proposed_schema": body.proposed_schema,
        "resolved_risks": body.resolved_risks,
        "unresolved_risks": body.unresolved_risks,
    }
    return await groq_client.ask(get_settings(), body.question, context)
