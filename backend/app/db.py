from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class SessionRow(Base):
    __tablename__ = "import_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)
    resolved_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[str] = mapped_column(String(64), default="")


class CreatedTableRow(Base):
    __tablename__ = "created_tables"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    catalog: Mapped[str] = mapped_column(String(128))
    schema_name: Mapped[str] = mapped_column(String(128))
    table_name: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[str] = mapped_column(String(64))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    size_label: Mapped[str] = mapped_column(String(64), default="")
    owner: Mapped[str] = mapped_column(String(256), default="")
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    created_json: Mapped[str] = mapped_column(Text)


_engine = None
_SessionLocal: Optional[sessionmaker] = None


def _normalize_url(url: str) -> str:
    # Neon / Render often provide postgres:// — SQLAlchemy wants postgresql+psycopg://
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def get_database_url() -> str:
    settings = get_settings()
    if settings.database_url.strip():
        return _normalize_url(settings.database_url.strip())
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'app.db').as_posix()}"


def init_db() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        return
    url = get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(_engine)


def db_session() -> Session:
    init_db()
    assert _SessionLocal is not None
    return _SessionLocal()


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, default=str)


def loads(raw: str) -> Any:
    return json.loads(raw)
