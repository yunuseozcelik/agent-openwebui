"""FastAPI application — Agent Factory backend.

Run:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routes.agents import router as agents_router
from .routes.analytics import router as analytics_router
from .routes.builder import router as builder_router
from .routes.templates import router as templates_router


app = FastAPI(
    title="Agent Factory API",
    description="Dogal dille AI agent uretim platformu.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(builder_router)
app.include_router(agents_router)
app.include_router(templates_router)
app.include_router(analytics_router)


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "agent-factory", "version": "2.0.0"}


@app.get("/api/debug/foundry")
async def debug_foundry():
    """Foundry baglanti durumunu kontrol et (gecici debug endpoint)."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        from agent_factory.deployment.foundry_client import _get_foundry_client
        client = _get_foundry_client()
    return {
        "client_ok": client is not None,
        "client_type": type(client).__name__ if client else None,
        "logs": buf.getvalue(),
    }


# ── Static frontend (prod build) ──
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"error": "Frontend build not found"}
else:

    @app.get("/")
    async def root():
        return {
            "service": "agent-factory",
            "status": "backend only — frontend dev: cd web && npm run dev",
            "api_docs": "/docs",
        }
