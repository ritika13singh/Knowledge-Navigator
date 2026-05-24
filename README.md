# Knowledge Navigator

A document Q&A platform built for Knowledge Navigator that lets staff search and query institutional knowledge using Retrieval-Augmented Generation (RAG). Upload PDFs, Word documents, and CSVs — then ask questions in plain English and get grounded answers with source citations.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the App](#running-the-app)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [RAG Pipeline](#rag-pipeline)
- [Google OAuth Setup](#google-oauth-setup)
- [Google Drive Monitor](#google-drive-monitor)
- [PostgreSQL Metrics (Optional)](#postgresql-metrics-optional)
- [Document Ingestion](#document-ingestion)
- [Frontend Development](#frontend-development)

---

## Overview

The Knowledge Navigator surfaces institutional documents through a conversational interface. Staff can ask questions like _"What is our climate resilience policy?"_ and receive answers grounded in actual uploaded documents, with source citations. Anonymous access is also supported for a public-facing portal.

**Key capabilities:**

- **Corrective RAG (CRAG):** Retrieves document chunks, grades their relevance with an LLM, rewrites the query if needed, and falls back to general knowledge with a disclaimer when no relevant documents are found.
- **Document management:** Upload PDF, TXT, and CSV files with metadata (themes, document type, visibility, description). Tag documents for thematic filtering.
- **Google Drive sync:** Point the app at a Drive folder and it automatically ingests new files on a configurable schedule.
- **Multi-turn conversation:** Maintains the last 10 messages as context for follow-up questions.
- **Metrics dashboard:** Tracks query volume, latency percentiles (P50/P95), and user feedback.
- **Admin panel:** Control which users have staff/admin access.
- **Chat history:** Authenticated users can save and resume past conversations (requires PostgreSQL).

---

## Architecture

```
Browser
  │
  ├── React SPA (port 3001 dev / served from /static in prod)
  │     ├── Public Portal  — anonymous access, public docs only
  │     ├── Staff Portal   — authenticated, all docs
  │     └── Dashboard      — metrics, ingest management, Drive monitor
  │
  └── FastAPI Backend (port 8000)
        ├── /api/auth/*       — Google OAuth + JWT session cookies
        ├── /api/query        — End-to-end Q&A (CRAG + LLM)
        ├── /api/rag/*        — Ingest, retrieve, manage documents
        ├── /api/drive/*      — Google Drive folder monitoring
        ├── /api/chat-history — Conversation persistence
        ├── /api/metrics/*    — Usage analytics
        └── /api/admin/*      — Admin user management

ChromaDB (local)       — Vector embeddings (persisted in chroma_db/)
PostgreSQL (optional)  — Metrics, document metadata, chat history, admin users
OpenAI API             — Embeddings (text-embedding-3-small), Q&A, grading, rewriting
```

In production the React build is served directly by FastAPI (no separate web server needed).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI + Uvicorn |
| Vector store | ChromaDB (local, persistent) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM (Q&A) | OpenAI `gpt-4o` (configurable) |
| LLM (grading/rewriting) | OpenAI `gpt-4o-mini` (configurable) |
| PDF parsing | pypdf |
| Token chunking | tiktoken (`cl100k_base`, 512 tokens, 128 overlap) |
| Auth | Google OAuth 2.0 + JWT (httpOnly cookie) |
| Database | PostgreSQL via psycopg2 (optional) |
| Frontend | React 19, React Router 7, react-icons |
| PDF export | jsPDF |
| Python version | 3.9+ |

---

## Project Structure

```
.
├── backend/
│   ├── main.py                  # FastAPI app entry point, CORS, static serving
│   ├── config.py                # All config/env vars in one place
│   ├── auth.py                  # JWT helpers, Google OAuth flow
│   ├── metrics_db.py            # PostgreSQL: query_metrics, feedback, admin_users tables
│   ├── documents_db.py          # PostgreSQL: document metadata table
│   ├── chat_history_db.py       # PostgreSQL: chat conversations table
│   ├── rag/
│   │   ├── chroma.py            # ChromaDB singleton (get_collection)
│   │   ├── ingest.py            # Parse → chunk → embed → store
│   │   ├── retrieve.py          # Embed query → ChromaDB similarity search
│   │   ├── grade.py             # LLM relevance grading per chunk
│   │   ├── rewrite.py           # LLM query rewriting
│   │   └── crag.py              # CRAG orchestrator (retrieve → grade → rewrite → fallback)
│   ├── services/
│   │   ├── llm_client.py        # OpenAI Chat Completions wrapper
│   │   └── rag_service.py       # Thin facade over CRAG layer
│   ├── routers/
│   │   ├── auth.py              # /api/auth/*
│   │   ├── health.py            # /api/health
│   │   ├── rag.py               # /api/rag/*, /api/query, /api/documents, /api/themes
│   │   ├── metrics.py           # /api/metrics/*
│   │   ├── chat_history.py      # /api/chat-history/*
│   │   ├── drive_monitor.py     # /api/drive/*
│   │   └── admin.py             # /api/admin/*
│   └── schemas/
│       └── rag.py               # Pydantic request/response models
├── frontend/nest/
│   ├── src/
│   │   ├── pages/               # Dashboard, PublicPortal, LoginPage, etc.
│   │   ├── components/          # Chat, ChatInput, AppLayout, SideNav, ThemeFilter, etc.
│   │   ├── context/
│   │   │   └── AuthContext.js   # Global auth state + getApiBase()
│   │   └── styles.css           # Single stylesheet (design system + all component styles)
│   └── build/                   # Production build (served by FastAPI)
├── data/
│   └── documents/               # Drop PDFs/TXTs/CSVs here for on-demand ingest
├── chroma_db/                   # ChromaDB persistent vector store (auto-created)
├── uploads/                     # Temporary storage for API-uploaded files
├── scripts/
│   ├── init_kn_db.sql        # PostgreSQL setup DDL
│   ├── ingest_hackathon_folder.py
│   └── rag_clear_and_reingest.py
├── docs/
│   ├── SETUP-GUIDE.md
│   ├── README-PROTOTYPE.md
│   └── Knowledge Navigator-Knowledge-Navigator-System-Design.md
├── .env.example                 # Copy to .env and fill in
├── requirements.txt
└── run.py                       # Backend launcher (python run.py)
```

---

## Prerequisites

- Python 3.9 or higher
- Node.js 18+ and npm
- An [OpenAI API key](https://platform.openai.com/api-keys)
- (Optional) PostgreSQL 14+ for metrics, document metadata, and chat history
- (Optional) A Google Cloud project for OAuth and Drive integration

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd "Knowledge Navigator"

python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` — the only required key is `OPENAI_API_KEY`:

```dotenv
OPENAI_API_KEY=sk-...
JWT_SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_urlsafe(32))">
```

See [Environment Variables](#environment-variables) for the full reference.

### 4. Build the React frontend

```bash
cd frontend/nest
npm install
npm run build
cd ../..
```

The build output lands in `frontend/nest/build/` and is served automatically by FastAPI at `/`.

---

## Running the App

```bash
# Activate virtualenv first
source .venv/bin/activate

# Start the backend (serves API + React build)
python run.py
```

Open **http://localhost:8000** in your browser.

For **frontend hot-reload during development**, run the backend and frontend separately:

```bash
# Terminal 1 — backend
python run.py

# Terminal 2 — frontend dev server (http://localhost:3001)
cd frontend/nest
npm start
```

Set `FRONTEND_ORIGIN=http://localhost:3001` in `.env` when running both separately.

---

## Environment Variables

All variables are read from `.env` in the project root. None crash the app if missing — features degrade gracefully.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | — | OpenAI key for embeddings, Q&A, CRAG grading, and query rewriting |
| `OPENAI_CHAT_MODEL` | No | `gpt-4o` | Model used to generate final Q&A answers |
| `OPENAI_GRADER_MODEL` | No | `gpt-4o-mini` | Model used for CRAG relevance grading and query rewriting |
| `JWT_SECRET_KEY` | Yes (for OAuth) | — | Long random string for signing session JWTs. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `GOOGLE_CLIENT_ID` | No | — | OAuth 2.0 client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | No | — | OAuth 2.0 client secret |
| `FRONTEND_ORIGIN` | No | `http://localhost:3001` | URL the browser runs on — used for post-login redirect and CORS |
| `DATABASE_URL` | No | — | PostgreSQL connection string, e.g. `postgresql://user:pass@localhost:5432/kn_db`. If unset, metrics/history are no-ops. |
| `PORT` | No | `8000` | Backend port |
| `APP_NAME` | No | `knowledge-navigator` | Application name used in logs |
| `N8N_SYNC_WEBHOOK_URL` | No | — | If set, a POST is fired to this URL on app startup (triggers n8n to sync Drive/uploads) |
| `DRIVE_WEBHOOK_SECRET` | No | — | If set, validates `X-Drive-Secret` header on `/api/drive/watch/tick` |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | — | Path to a Google service account JSON file (for Drive API without user OAuth) |
| `AUTH_COOKIE_MAX_AGE` | No | `604800` | Session cookie lifetime in seconds (default: 7 days) |

---

## API Reference

All endpoints are prefixed with `/api`. Authentication uses an httpOnly JWT cookie (`kn_session`) set at login.

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | None | Health check; returns `{"status": "ok", "authenticated": bool}` |

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/auth/google` | None | Redirect to Google OAuth consent screen |
| GET | `/api/auth/callback` | None | OAuth callback — sets session cookie and redirects to frontend |
| GET | `/api/auth/me` | Optional | Returns current user info (`email`, `name`, `is_admin`) |
| POST | `/api/auth/logout` | Optional | Clears session cookie |

### Q&A

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/query` | Optional | End-to-end Q&A. Body: `{prompt, history?, themes?, public_mode?}`. Returns `{answer, sources, rag_path, chunks_retrieved, chunks_relevant, rewritten_query?}` |

### RAG & Document Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/rag/insert/file` | Admin | Upload and ingest a file (multipart). Fields: `file`, `title`, `description`, `themes` (JSON array), `document_type`, `visibility` |
| POST | `/api/rag/delete/file` | Admin | Delete a file from the vector index. Body: `{file_name}` |
| POST | `/api/rag/retrieve` | Any | Retrieve top-K chunks for a query. Body: `{query, n_results?, themes?}` |
| POST | `/api/rag/clear` | Admin | Wipe the entire ChromaDB index |
| POST | `/api/rag/ingest/data-dir` | Admin | Start background ingestion of all files in `data/documents/`. Returns immediately; poll `/api/rag/ingest/status` for progress. |
| GET | `/api/rag/ingest/status` | Admin | Live ingest job status: `{running, processed, total, current_file, results, finished_at}` |
| GET | `/api/documents` | Any | List documents. Query params: `themes`, `document_type`, `date_from`, `date_to`, `internal_only` |
| GET | `/api/documents/{file_name}` | Any | Get one document's metadata |
| PUT | `/api/documents/{file_name}` | Admin | Update document metadata |
| DELETE | `/api/documents/{file_name}` | Admin | Remove document metadata record |
| GET | `/api/themes` | Any | All themes with document counts |
| GET | `/api/document-types` | Any | All document types |

### Google Drive Monitor

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/drive/watch` | Any auth | Start monitoring a Drive folder. Body: `{folder_id, folder_name?, interval_seconds?, use_personal_drive?}` |
| GET | `/api/drive/watch/status` | Any auth | Current monitoring state |
| POST | `/api/drive/watch/stop` | Any auth | Stop monitoring |
| POST | `/api/drive/watch/tick` | Optional (webhook secret) | Manually trigger one check cycle (for cron/webhook use) |

### Chat History

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/chat-history/conversations` | Required | List all saved conversations |
| GET | `/api/chat-history/conversations/{id}` | Required | Get one conversation with messages |
| POST | `/api/chat-history/conversations` | Required | Upsert a conversation. Body: `{conversation_id, title, messages}` |
| DELETE | `/api/chat-history/conversations/{id}` | Required | Delete a conversation |

### Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/check/{email}` | None | Check if an email has admin access |
| GET | `/api/admin/users` | Admin | List all admin users |
| POST | `/api/admin/users` | Admin | Add an admin user. Body: `{email}` |
| DELETE | `/api/admin/users/{email}` | Admin | Remove an admin user (cannot remove yourself) |

### Metrics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/metrics/summary` | Any | Query count, avg/P50/P95 latency, feedback counts. Query params: `date_from`, `date_to` |
| POST | `/api/metrics/feedback` | Any | Submit feedback. Body: `{query_id, helpful: bool}` |

---

## RAG Pipeline

Every call to `/api/query` runs the full CRAG pipeline:

```
1. Embed the user's question (text-embedding-3-small)
2. Query ChromaDB for the top-5 most similar chunks
3. Grade each chunk for relevance using gpt-4o-mini
   ├── ≥1 relevant chunk → proceed with those chunks
   └── 0 relevant chunks →
         4a. Rewrite the query (gpt-4o-mini)
         4b. Re-embed and re-query ChromaDB
         └── Still 0 relevant → fallback to LLM general knowledge
                                 (answer prefixed with disclaimer)
5. Build a system prompt with the relevant chunks as context
6. Call gpt-4o (configurable) with the full conversation history
7. Return answer + source citations + pipeline metadata
   (rag_path: "direct" | "rewritten" | "fallback")
```

**Chunking:** tiktoken `cl100k_base` encoding, 512-token chunks, 128-token overlap.

**Thematic filtering:** Pass `themes: ["climate", "governance"]` in the query body to restrict retrieval to documents tagged with those themes.

**Public mode:** Pass `public_mode: true` to exclude internal-only documents and memos. Used by the public portal.

---

## Google OAuth Setup

Skip this section if you only need anonymous access.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add an authorized redirect URI:
   - Development: `http://localhost:8000/api/auth/callback`
   - Production: `https://your-domain.com/api/auth/callback`
4. Copy the **Client ID** and **Client Secret** into `.env`
5. Go to **OAuth consent screen** → add your email as a **Test user** (required while the app is in testing mode)

```dotenv
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
JWT_SECRET_KEY=<random string>
FRONTEND_ORIGIN=http://localhost:3001
```

The first user to log in will not have admin access by default. To bootstrap an admin, insert a row directly:

```sql
INSERT INTO admin_users (email) VALUES ('you@example.com');
```

Or use the admin API after granting yourself access via the DB.

---

## Google Drive Monitor

The Drive Monitor watches a Google Drive folder and automatically ingests new PDF, TXT, and CSV files into ChromaDB.

**Using your personal Google account (recommended for development):**
1. Sign in with Google OAuth (see above)
2. Go to **Dashboard → Drive Monitor**
3. Select "Use my Google account" and pick a folder
4. Click **Start monitoring**

**Using a service account (for production/server-side use):**
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json` in `.env`
4. Share the target Drive folder with the service account email

The monitor polls the folder every 60 seconds by default. Only files not already in ChromaDB are ingested (no duplicate embedding costs).

---

## PostgreSQL Metrics (Optional)

The app runs fully without PostgreSQL — metrics endpoints return empty data and chat history is not persisted. To enable:

### 1. Create the database

```bash
psql postgres < scripts/init_kn_db.sql
```

Or manually:

```sql
CREATE USER kn_app WITH PASSWORD 'yourpassword';
CREATE DATABASE kn_db OWNER kn_app;
```

### 2. Set DATABASE_URL

```dotenv
DATABASE_URL=postgresql://kn_app:yourpassword@localhost:5432/kn_db
```

Tables are created automatically on app startup (`query_metrics`, `feedback`, `admin_users`, `documents`, `chat_conversations`).

### macOS quick start (Homebrew)

```bash
brew install postgresql@14
brew services start postgresql@14
createdb kn
psql kn < scripts/init_kn_db.sql
```

---

## Document Ingestion

### Option A — Drop files and ingest via Dashboard

1. Put PDF, TXT, or CSV files in `data/documents/`
2. Go to **Dashboard → Local Ingest**
3. Click **Start Ingest** — files already in ChromaDB are skipped automatically

### Option B — Upload via API

```bash
curl -X POST http://localhost:8000/api/rag/insert/file \
  -H "Cookie: kn_session=<your-jwt>" \
  -F "file=@report.pdf" \
  -F "title=Annual Report 2024" \
  -F 'themes=["climate","impact"]' \
  -F "document_type=report" \
  -F "visibility=internal"
```

### Option C — Bulk reingest script

```bash
python scripts/rag_clear_and_reingest.py
```

### Supported file types

| Extension | Parser |
|-----------|--------|
| `.pdf` | pypdf (text extraction) |
| `.txt` | UTF-8 read |
| `.csv` | Row-by-row text |

Files are chunked at 512 tokens with 128-token overlap before embedding.

---

## Frontend Development

The React app lives in `frontend/nest/`.

```bash
cd frontend/nest
npm install
npm start          # dev server at http://localhost:3001 with hot reload
npm run build      # production build → frontend/nest/build/
npm test           # run tests
```

**Key files:**

| File | Purpose |
|------|---------|
| `src/context/AuthContext.js` | Auth state (`user`, `loading`, `loginUrl`) + `getApiBase()` |
| `src/pages/Dashboard.js` | Metrics dashboard, Local Ingest tab, Drive Monitor tab |
| `src/pages/PublicPortal.js` | Anonymous public interface |
| `src/components/ProtectedRoute.js` | Redirects unauthenticated users to login |
| `src/styles.css` | Complete design system (CSS custom properties, all component styles) |

**Design tokens** (defined in `.theme-dark` scope in `styles.css`):

```css
--nav-bg: #1e293b
--nav-accent: #00c789
--page-text: #e2e8f0
--chat-muted: #94a3b8
```

All new UI components should use these tokens and follow the `dashboard__*` or `dp-*` BEM-style class naming.

**Proxy:** During development, API calls from the React dev server (port 3001) are proxied to the backend (port 8000) via the `proxy` field in `package.json`.
