from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.db import init_db

settings = get_settings()

app = FastAPI(
    title="Import Confidence Check API",
    description="Deterministic conversion-risk scanner for Databricks-style file uploads",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _static_root() -> Path | None:
    candidates = []
    if settings.static_dir.strip():
        candidates.append(Path(settings.static_dir))
    here = Path(__file__).resolve()
    candidates.extend(
        [
            here.parents[1] / "static",
            here.parents[2] / "frontend" / "out",
        ]
    )
    for path in candidates:
        if path.is_dir() and (path / "index.html").exists():
            return path
    return None


_STATIC = _static_root()
if _STATIC is not None:
    assets = _STATIC / "_next"
    if assets.exists():
        app.mount("/_next", StaticFiles(directory=assets), name="next-assets")

    @app.get("/")
    def spa_index() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str, request: Request):
        if full_path.startswith(("api/", "docs", "openapi.json", "redoc")) or full_path in {
            "docs",
            "openapi.json",
            "redoc",
        }:
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (_STATIC / full_path).resolve()
        try:
            candidate.relative_to(_STATIC.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        if candidate.is_file():
            return FileResponse(candidate)
        nested = _STATIC / full_path / "index.html"
        if nested.is_file():
            return FileResponse(nested)
        return FileResponse(_STATIC / "index.html")
else:

    @app.get("/")
    def root() -> dict:
        return {"service": "import-confidence-check", "docs": "/docs"}
