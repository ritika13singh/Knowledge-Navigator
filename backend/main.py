"""
Knowledge Navigator — Prototype API.

Structure:
- routers/health.py  — /api/health (no auth)
- routers/rag.py     — /api/rag/* and /api/query (RAG + Anthropic LLM)
- routers/metrics.py — /api/metrics/* (metrics DB)
- services/rag_service.py — RAG ingest/retrieve (implement your vector store here)
- services/llm_client.py  — Anthropic Messages API for chat
- metrics_db.py     — PostgreSQL metrics (query_metrics, feedback tables)

Startup: if N8N_SYNC_WEBHOOK_URL is set, app triggers that webhook once on startup so n8n
can run sync from Drive/uploads and ingest files into RAG.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

import dotenv

# Load .env before importing config (so DATABASE_URL etc. are set)
_root = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(_root / ".env")

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from backend.config import CORS_ORIGINS, N8N_SYNC_WEBHOOK_URL, PROJECT_ROOT
from backend.routers import auth, health, metrics, rag, drive_monitor, chat_history, admin
from backend import metrics_db, documents_db, chat_history_db


class SPAStaticFiles(StaticFiles):
    """Serve static files and fall back to index.html for SPA client-side routes."""

    async def get_response(self, path: str, scope: dict):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code != 404:
                raise
            # Fall back to index.html so client-side router can handle /login, etc.
            index_path = os.path.join(self.directory or "", "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            raise


def _trigger_n8n_sync_on_startup() -> None:
    """Fire-and-forget: POST to n8n webhook so it runs sync (Drive/uploads → ingest)."""
    if not N8N_SYNC_WEBHOOK_URL:
        return
    import threading

    def _post():
        try:
            import requests
            requests.post(N8N_SYNC_WEBHOOK_URL, json={"source": "kn-app-startup"}, timeout=10)
        except Exception:
            pass

    threading.Thread(target=_post, daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure PostgreSQL metrics tables exist (no-op if DATABASE_URL not set)
    ok = metrics_db.ensure_tables()
    if ok:
        print("Metrics DB: tables ensured (query_metrics, feedback).")
    else:
        print("Metrics DB: not configured (set DATABASE_URL in .env to enable).")

    # Ensure documents metadata table exists
    docs_ok = documents_db.ensure_tables()
    if docs_ok:
        print("Documents DB: table ensured (documents).")

    # Ensure chat history table exists
    chat_ok = chat_history_db.ensure_tables()
    if chat_ok:
        print("Chat History DB: table ensured (chat_conversations).")

    # Startup: optionally trigger n8n to ingest files from Drive/uploads (non-blocking)
    _trigger_n8n_sync_on_startup()
    yield


app = FastAPI(
    title="Knowledge Navigator (Prototype)",
    description="RAG ingest, retrieve, and Q&A over institutional knowledge.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(rag.router)
app.include_router(metrics.router)
app.include_router(drive_monitor.router)
app.include_router(chat_history.router)
app.include_router(admin.router)

# Serve React app from frontend/nest/build (run: cd frontend/nest && npm run build)
# Note: mount must come AFTER routers so /api/* routes are handled by FastAPI, not the SPA
nest_build = PROJECT_ROOT / "frontend" / "nest" / "build"
static_dir = nest_build / "static"
index_html = nest_build / "index.html"
if static_dir.exists() and index_html.exists():
    # Use html=False to prevent catching all routes; SPAStaticFiles handles 404->index.html fallback
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        # Don't serve SPA for API routes
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        file_path = nest_build / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(nest_build / "index.html")

    print("Frontend: serving React app from frontend/nest/build")
else:
    # Fallback: single index.html if present
    legacy_index = PROJECT_ROOT / "frontend" / "index.html"
    if legacy_index.exists():
        @app.get("/")
        def index():
            return FileResponse(legacy_index)
        print("Frontend: serving legacy single-page app (frontend/index.html). To use the React app, run: cd frontend/nest && npm install && npm run build")
    elif nest_build.exists():
        print("Frontend build incomplete (missing build/static or index.html). Run: cd frontend/nest && npm run build")
    else:
        print("Frontend not built. Run: cd frontend/nest && npm install && npm run build")


if __name__ == "__main__":
    from backend.config import BACKEND_PORT
    uvicorn.run(
        "backend.main:app",
        host="localhost",
        port=BACKEND_PORT,
        reload=True,
    )
