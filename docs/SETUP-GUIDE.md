# Knowledge Navigator — Setup Guide

Follow these steps in order. All commands assume you are in the project root.

---

## 1. Python environment

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# Windows: .venv\Scripts\activate
```

---

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure environment variables

Copy the example file and edit it:

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

- **OPENAI_API_KEY** — Your OpenAI API key (required for embeddings, Q&A, CRAG grading, and query rewriting).

Optional model overrides (defaults shown):

- **OPENAI_CHAT_MODEL** — Model for final answers (default: `gpt-4o`).
- **OPENAI_GRADER_MODEL** — Model for CRAG grading and query rewriting (default: `gpt-4o-mini`).

Optional for metrics (can add later):

- **DATABASE_URL** — PostgreSQL connection string (see step 5). If unset, the app runs but does not store metrics.

No spaces around `=`. Example:

```
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://kn_app:your_password@localhost:5432/kn_db
```

---

## 4. Install PostgreSQL (if you want metrics)

**macOS (Homebrew):**

```bash
brew install postgresql@16
brew services start postgresql@16
```

**Docker:**

```bash
docker run -d --name kn-pg -e POSTGRES_PASSWORD=kn -e POSTGRES_DB=kn -p 5432:5432 postgres:16-alpine
```

Then use in `.env`: `DATABASE_URL=postgresql://postgres:kn@localhost:5432/kn_db` and skip step 5 (database already exists).

---

## 5. Create the database (if not using Docker above)

On macOS the default PostgreSQL user is your Mac username, not `postgres`. Run:

```bash
psql -d postgres -f scripts/init_kn_db.sql
```

This creates user `kn_app`, database `kn`, and permissions. Then in `.env` set:

```
DATABASE_URL=postgresql://kn_app:change_me_in_production@localhost:5432/kn_db
```

(Change the password in production.)

Verify:

```bash
psql "postgresql://kn_app:change_me_in_production@localhost:5432/kn_db" -c "SELECT 1;"
```

---

## 6. Build the React frontend (recommended)

To use the **nest** React app instead of the legacy single-page HTML:

```bash
cd frontend/nest && npm install && npm run build && cd ../..
```

After the build, the server will serve the React app from `frontend/nest/build`. If you skip this step, the server falls back to `frontend/index.html`. Startup logs will show which frontend is being served.

---

## 7. Run the app

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python run.py
```

You should see:

- `Frontend: serving React app from frontend/nest/build` — React app is active (after step 6).
- Or `Frontend: serving legacy single-page app` — legacy UI; run step 6 to switch to React.
- `Metrics DB: tables ensured (query_metrics, feedback).` — DB connected; metrics tables created.
- `Metrics DB: not configured` — App will run; no metrics stored until `DATABASE_URL` is set.

---

## 8. Google Sign-In (optional)

To enable "Sign in with Google":

1. **Google Cloud Console** — Create OAuth 2.0 credentials (APIs & Services → Credentials → Create credentials → OAuth client ID). Use "Web application", add authorized redirect URI: `http://localhost:8000/api/auth/callback` (or your backend URL in production).

2. **Environment variables** — In `.env` set:
   - `GOOGLE_CLIENT_ID` — from the OAuth client
   - `GOOGLE_CLIENT_SECRET` — from the OAuth client
   - `JWT_SECRET_KEY` — a long random string (e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
   - `FRONTEND_ORIGIN` — where the frontend runs (e.g. `http://localhost:3000` when using `npm start`, or `http://localhost:8000` when using the built app from the same server)

3. **Development with separate frontend** — If you run the React dev server (`npm start` in `frontend/nest`) and the backend on port 8000, set in `frontend/nest/.env`: `REACT_APP_API_URL=http://localhost:8000`. This ensures the "Login" link and API calls go to the backend. CORS is set to allow both origins when `FRONTEND_ORIGIN` is set.

Without these variables, the app runs normally but "Sign in with Google" will redirect to the login page with an error. Everyone can still use the chat; authenticated users get full source lists and an `authenticated: true` flag in API responses.

### Admin users (DB check)

On login, the app checks the user's email against the `admin_users` table. If the email exists, the session gets `is_admin: true` (returned in `GET /api/auth/me` and in `AuthUser` for backend routes).

1. Ensure the app has run once with `DATABASE_URL` set so the `admin_users` table exists.
2. Add an admin by email:  
   `psql "postgresql://kn_app:YOUR_PASSWORD@localhost:5432/kn_db" -c "INSERT INTO admin_users (email) VALUES ('admin@example.com') ON CONFLICT (email) DO NOTHING;"`
3. The user must sign out and sign in again for `is_admin` to be set.

---

## 9. Verify

- Open **http://localhost:8000** in your browser.
- Upload a file (PDF, TXT, or CSV) and ask a question.

If you use a PostgreSQL GUI (DBeaver, pgAdmin, TablePlus), connect to the `kn` database with the same user/password as in `DATABASE_URL`. After the app has started once with `DATABASE_URL` set, you will see tables `query_metrics` and `feedback` under **Schemas → public → Tables**. Refresh the tree if they do not appear.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Still seeing old chat UI | Run `cd frontend/nest && npm install && npm run build`. Restart the server; you should see "Frontend: serving React app from frontend/nest/build". Hard-refresh the browser (Ctrl+Shift+R / Cmd+Shift+R). |
| `role "postgres" does not exist` | On macOS use `psql -d postgres` (no `-U postgres`). |
| No tables in DB GUI | Ensure `DATABASE_URL` is in `.env` with no spaces around `=`, then restart the app. Check startup log for "Metrics DB: tables ensured". |
| Missing OPENAI_API_KEY error | Set `OPENAI_API_KEY=` in `.env` with your OpenAI API key. |
| RAG not configured / 503 on upload or retrieve | Ensure `OPENAI_API_KEY` is set; ChromaDB initialises on first upload. |
| Google sign-in redirects with error | Ensure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `JWT_SECRET_KEY` are set in `.env`. Add `http://localhost:8000/api/auth/callback` (or your backend URL) to authorized redirect URIs in Google Cloud Console. |
| CORS / credentials errors when using npm start | Set `REACT_APP_API_URL=http://localhost:8000` in `frontend/nest/.env` and ensure `FRONTEND_ORIGIN=http://localhost:3000` in backend `.env`. |
| User not showing as admin after adding to admin_users | User must sign out and sign in again; admin status is set at login time. |
