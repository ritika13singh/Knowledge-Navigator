-- Create PostgreSQL database and user for Knowledge Navigator (metrics).
-- On macOS (Homebrew) the default superuser is your Mac username, not "postgres". Run:
--   psql -d postgres -f scripts/init_kn_db.sql
-- (Do not use -U postgres unless that role exists.)
-- Then set in .env: DATABASE_URL=postgresql://kn_app:YOUR_PASSWORD@localhost:5432/kn_db

CREATE USER kn_app WITH PASSWORD 'change_me_in_production';

CREATE DATABASE kn_db OWNER kn_app;

GRANT ALL PRIVILEGES ON DATABASE kn_db TO kn_app;

\c kn_db

GRANT ALL ON SCHEMA public TO kn_app;

-- Tables (query_metrics, feedback) are created by the app on startup via metrics_db.ensure_tables().
