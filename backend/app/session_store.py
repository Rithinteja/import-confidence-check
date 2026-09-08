from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select

from app.config import get_settings
from app.db import CreatedTableRow, SessionRow, db_session, dumps, init_db, loads
from app.models import (
    ColumnSchema,
    CreatedTableResponse,
    ImportRisk,
    ImportSessionResponse,
    ParsedTable,
)
from app.scanner.engine import confidence_status, scan_table
from app.services.convert import materialize_row
from app.services.infer import infer_columns
from app.services.parse import suggest_table_name


class ImportSession:
    def __init__(self, parsed: ParsedTable, session_id: Optional[str] = None):
        settings = get_settings()
        self.session_id = session_id or str(uuid4())
        self.parsed = parsed
        # Databricks JSON Advanced attribute: Infer timestamp (on by default for JSON).
        self.infer_timestamps = parsed.format == "json"
        self.columns: list[ColumnSchema] = infer_columns(
            parsed.headers,
            parsed.rows,
            infer_timestamps=self.infer_timestamps,
            source_format=parsed.format,
        )
        self.catalog = "dbacademy"
        self.schema_name = "default"
        self.table_name = suggest_table_name(parsed.filename)
        self.action = "Create new table"
        self.resolved_risk_ids: set[str] = set()
        self.created: Optional[CreatedTableResponse] = None
        self.preview_limit = settings.preview_row_limit
        self._risk_snapshot: list[ImportRisk] = []
        self.rescan()

    def reinfer_columns(self) -> None:
        self.columns = infer_columns(
            self.parsed.headers,
            self.parsed.rows,
            infer_timestamps=self.infer_timestamps,
            source_format=self.parsed.format,
        )

    def rescan(self) -> list[ImportRisk]:
        risks = scan_table(
            self.parsed.headers,
            self.parsed.rows,
            self.columns,
            preview_limit=self.preview_limit,
        )
        self._risk_snapshot = risks
        current_ids = {r.risk_id for r in risks}
        self.resolved_risk_ids &= current_ids
        return risks

    @property
    def risks(self) -> list[ImportRisk]:
        return self._risk_snapshot

    def to_payload(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "parsed": self.parsed.model_dump(),
            "columns": [c.model_dump(mode="json") for c in self.columns],
            "catalog": self.catalog,
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "action": self.action,
            "infer_timestamps": self.infer_timestamps,
            "resolved_risk_ids": sorted(self.resolved_risk_ids),
            "preview_limit": self.preview_limit,
            "created": self.created.model_dump(mode="json", by_alias=True) if self.created else None,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ImportSession":
        parsed = ParsedTable.model_validate(payload["parsed"])
        session = cls.__new__(cls)
        session.session_id = payload["session_id"]
        session.parsed = parsed
        session.infer_timestamps = bool(
            payload.get("infer_timestamps", parsed.format == "json")
        )
        session.columns = [ColumnSchema.model_validate(c) for c in payload.get("columns", [])]
        session.catalog = payload.get("catalog", "dbacademy")
        session.schema_name = payload.get("schema_name", "default")
        session.table_name = payload.get("table_name", suggest_table_name(parsed.filename))
        session.action = payload.get("action", "Create new table")
        session.resolved_risk_ids = set(payload.get("resolved_risk_ids", []))
        session.preview_limit = payload.get("preview_limit", get_settings().preview_row_limit)
        created_raw = payload.get("created")
        session.created = (
            CreatedTableResponse.model_validate(created_raw) if created_raw else None
        )
        session._risk_snapshot = []
        session.rescan()
        return session

    def to_response(self, previously_resolved: int = 0) -> ImportSessionResponse:
        risks = self.risks
        unresolved = len(risks)
        resolved = previously_resolved
        status = confidence_status(unresolved, resolved)
        if unresolved > 0 and resolved == 0:
            status = f"{unresolved} import risks found"
        preview = []
        for row in self.parsed.rows[: self.preview_limit]:
            preview.append(materialize_row(row, self.columns))
        outside = any(r.outside_preview_count > 0 for r in risks)
        return ImportSessionResponse(
            session_id=self.session_id,
            filename=self.parsed.filename,
            size_bytes=self.parsed.size_bytes,
            format=self.parsed.format,
            catalog=self.catalog,
            schema_name=self.schema_name,
            table_name=self.table_name,
            action=self.action,
            columns=self.columns,
            preview_rows=preview,
            preview_limit=self.preview_limit,
            total_rows=len(self.parsed.rows),
            risks=risks,
            confidence_status=status,
            unresolved_count=unresolved,
            resolved_count=resolved,
            risks_outside_preview=outside,
            infer_timestamps=self.infer_timestamps,
            show_infer_timestamps=self.parsed.format == "json",
        )


class SessionStore:
    def __init__(self) -> None:
        self._lock = Lock()
        init_db()

    def _save_session(self, session: ImportSession, resolved_count: Optional[int] = None) -> None:
        with db_session() as db:
            row = db.get(SessionRow, session.session_id)
            if row is None:
                row = SessionRow(
                    session_id=session.session_id,
                    payload=dumps(session.to_payload()),
                    resolved_count=resolved_count or 0,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                db.add(row)
            else:
                row.payload = dumps(session.to_payload())
                if resolved_count is not None:
                    row.resolved_count = resolved_count
                row.updated_at = datetime.now(timezone.utc).isoformat()
            db.commit()

    def create(self, parsed: ParsedTable) -> ImportSession:
        session = ImportSession(parsed)
        with self._lock:
            self._save_session(session, resolved_count=0)
        return session

    def get(self, session_id: str) -> ImportSession:
        with self._lock:
            with db_session() as db:
                row = db.get(SessionRow, session_id)
                if not row:
                    raise KeyError("Session not found")
                return ImportSession.from_payload(loads(row.payload))

    def bump_resolved(self, session_id: str) -> int:
        with self._lock:
            with db_session() as db:
                row = db.get(SessionRow, session_id)
                if not row:
                    raise KeyError("Session not found")
                row.resolved_count = int(row.resolved_count or 0) + 1
                db.commit()
                return row.resolved_count

    def resolved_count(self, session_id: str) -> int:
        with self._lock:
            with db_session() as db:
                row = db.get(SessionRow, session_id)
                return int(row.resolved_count) if row else 0

    def persist(self, session: ImportSession) -> None:
        with self._lock:
            self._save_session(session)

    def response(self, session: ImportSession) -> ImportSessionResponse:
        return session.to_response(previously_resolved=self.resolved_count(session.session_id))

    def create_table(self, session: ImportSession, force: bool = False) -> CreatedTableResponse:
        risks = session.risks
        high = [r for r in risks if r.severity.value == "high"]
        if high and not force:
            raise ValueError(
                "High-severity conversion risks remain. Fix them or create anyway with force=true."
            )

        sample_rows: list[dict[str, Any]] = []
        for row in session.parsed.rows[:20]:
            sample_rows.append(materialize_row(row, session.columns))

        size_kb = max(session.parsed.size_bytes / 1024, 0.1)
        summary = []
        if not risks:
            summary.append("No unresolved conversion risks")
        for col in session.columns:
            if col.type.value == "string":
                summary.append(f"{col.name} stored as String")
        for r in risks:
            summary.append(f"Unresolved: {r.title or r.risk_id}")

        created = CreatedTableResponse(
            catalog=session.catalog,
            schema_name=session.schema_name,
            table_name=session.table_name,
            columns=session.columns,
            sample_rows=sample_rows,
            total_rows=len(session.parsed.rows),
            created_at=datetime.now(timezone.utc).isoformat(),
            size_label=f"{size_kb:.1f}KiB",
            import_summary=summary[:8],
            unresolved_risks=risks,
        )
        session.created = created
        meta = {
            "session_id": session.session_id,
            "catalog": created.catalog,
            "schema": created.schema_name,
            "table_name": created.table_name,
            "created_at": created.created_at,
            "total_rows": created.total_rows,
            "size_label": created.size_label,
            "owner": created.owner,
        }
        with self._lock:
            self._save_session(session)
            with db_session() as db:
                row = db.get(CreatedTableRow, session.session_id)
                if row is None:
                    row = CreatedTableRow(
                        session_id=session.session_id,
                        catalog=created.catalog,
                        schema_name=created.schema_name,
                        table_name=created.table_name,
                        created_at=created.created_at,
                        total_rows=created.total_rows,
                        size_label=created.size_label,
                        owner=created.owner,
                        meta_json=dumps(meta),
                        created_json=dumps(created.model_dump(mode="json", by_alias=True)),
                    )
                    db.add(row)
                else:
                    row.catalog = created.catalog
                    row.schema_name = created.schema_name
                    row.table_name = created.table_name
                    row.created_at = created.created_at
                    row.total_rows = created.total_rows
                    row.size_label = created.size_label
                    row.owner = created.owner
                    row.meta_json = dumps(meta)
                    row.created_json = dumps(created.model_dump(mode="json", by_alias=True))
                db.commit()
        return created

    def list_tables(self) -> list[dict[str, Any]]:
        with self._lock:
            with db_session() as db:
                rows = db.scalars(
                    select(CreatedTableRow).order_by(CreatedTableRow.created_at.desc())
                ).all()
                return [loads(r.meta_json) for r in rows]

    def get_created(self, session_id: str) -> CreatedTableResponse:
        with self._lock:
            with db_session() as db:
                row = db.get(CreatedTableRow, session_id)
                if row:
                    return CreatedTableResponse.model_validate(loads(row.created_json))
            session = self.get(session_id)
            if not session.created:
                raise KeyError("Table not created yet")
            return session.created


store = SessionStore()
