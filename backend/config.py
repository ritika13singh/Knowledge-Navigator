"""Configuration for NESsT Knowledge Navigator."""
import os
from pathlib import Path

# ----- Hardcoded ports (override with env if needed) -----
BACKEND_PORT = int(os.getenv("PORT", "8000"))
FRONTEND_DEV_PORT = 3001  # used when running npm start; set PORT in frontend/nest/.env to match

# OpenAI — embeddings, chat, CRAG grading, and query rewriting
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_GRADER_MODEL = os.getenv("OPENAI_GRADER_MODEL", "gpt-4o-mini")

# Optional: app name for logging and context
APP_NAME = os.getenv("APPNAME", "nesst-knowledge-navigator")

# Prototype paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types for RAG insert
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv"}
# None = no limit (infinite); or set e.g. 20 for 20 MB
MAX_FILE_SIZE_MB = None

# Optional: trigger n8n sync when app starts (fire-and-forget)
N8N_SYNC_WEBHOOK_URL = os.getenv("N8N_SYNC_WEBHOOK_URL", "").strip() or None

# PostgreSQL for metrics (and document metadata). If unset, metrics are no-op.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or None

# Google OAuth (for "Sign in with Google")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip() or None
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip() or None
# Where to redirect after login (default: frontend dev server; same as backend when serving build)
_raw_origin = os.getenv("FRONTEND_ORIGIN", f"http://localhost:{FRONTEND_DEV_PORT}").strip()
# Never redirect to 3000 when frontend dev port is 3001 (avoid stale .env or old process)
if _raw_origin.rstrip("/") == "http://localhost:3000" and FRONTEND_DEV_PORT == 3001:
    FRONTEND_ORIGIN = f"http://localhost:{FRONTEND_DEV_PORT}"
else:
    FRONTEND_ORIGIN = _raw_origin
# CORS: when using credentials (cookies), origins cannot be "*". Comma-separated list, or set to FRONTEND_ORIGIN + backend origin.
_cors = os.getenv("CORS_ORIGINS", "").strip()
CORS_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()] if _cors else [FRONTEND_ORIGIN, f"http://localhost:{BACKEND_PORT}"]
# JWT secret for signing session tokens (use a long random string in production)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip() or None
# Session cookie name and max age (seconds; 7 days default)
AUTH_COOKIE_NAME = "nesst_session"
AUTH_COOKIE_MAX_AGE = int(os.getenv("AUTH_COOKIE_MAX_AGE", "604800"))  # 7 days
