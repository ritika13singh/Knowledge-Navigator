-- Create PostgreSQL database and user for NESsT Knowledge Navigator (metrics).
-- On macOS (Homebrew) the default superuser is your Mac username, not "postgres". Run:
--   psql -d postgres -f scripts/init_nesst_db.sql
-- (Do not use -U postgres unless that role exists.)
-- Then set in .env: DATABASE_URL=postgresql://nesst_app:YOUR_PASSWORD@localhost:5432/nesst

CREATE USER nesst_app WITH PASSWORD 'change_me_in_production';

CREATE DATABASE nesst OWNER nesst_app;

GRANT ALL PRIVILEGES ON DATABASE nesst TO nesst_app;

\c nesst

GRANT ALL ON SCHEMA public TO nesst_app;

-- Tables (query_metrics, feedback) are created by the app on startup via metrics_db.ensure_tables().
