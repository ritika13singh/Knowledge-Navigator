"""
Metrics DB — PostgreSQL tables for query metrics and optional feedback.

Uses DATABASE_URL from config. If unset, all functions no-op or return stub data.
Tables: query_metrics (per-request), feedback (was this helpful?).
"""
from __future__ import annotations
from typing import Optional

import logging
from contextlib import contextmanager

from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)

# Table names (single "collection" of metrics = query_metrics + feedback)
TABLE_QUERY_METRICS = "query_metrics"
TABLE_FEEDBACK = "feedback"
TABLE_ADMIN_USERS = "admin_users"


def _get_conn():
    """Return a DB connection or None if DATABASE_URL is not set."""
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.warning("Metrics DB connect failed: %s", e)
        return None


@contextmanager
def _connection():
    """Context manager for a single connection. Commits on success, rolls back on error."""
    conn = _get_conn()
    if conn is None:
        yield None
        return
    try:
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def ensure_tables() -> bool:
    """
    Create metrics tables if they do not exist. Call once at app startup.
    Returns True if tables were created or already exist, False if DB not configured.
    """
    with _connection() as conn:
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS query_metrics (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255),
                        endpoint VARCHAR(255) NOT NULL,
                        latency_seconds REAL NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS feedback (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255),
                        helpful BOOLEAN NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_users (
                        email VARCHAR(255) PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            return True
        except Exception as e:
            logger.warning("Metrics DB ensure_tables failed: %s", e)
            return False


def is_admin(email: Optional[str]) -> bool:
    """
    Return True if the given email exists in admin_users (case-insensitive).
    Returns False if email is None, DATABASE_URL is unset, or the email is not in the table.
    """
    if not email or not email.strip():
        return False
    with _connection() as conn:
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM admin_users WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s)) LIMIT 1",
                    (email,),
                )
                return cur.fetchone() is not None
        except Exception as e:
            logger.warning("is_admin check failed: %s", e)
            return False


def add_admin(email: str) -> bool:
    """
    Add an email to the admin_users table.
    Returns True on success, False on failure or if DB not configured.
    """
    if not email or not email.strip():
        return False
    with _connection() as conn:
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO admin_users (email)
                    VALUES (LOWER(TRIM(%s)))
                    ON CONFLICT (email) DO NOTHING
                    """,
                    (email,),
                )
            return True
        except Exception as e:
            logger.warning("add_admin failed: %s", e)
            return False


def remove_admin(email: str) -> bool:
    """
    Remove an email from the admin_users table.
    Returns True on success, False on failure or if DB not configured.
    """
    if not email or not email.strip():
        return False
    with _connection() as conn:
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM admin_users WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))",
                    (email,),
                )
            return True
        except Exception as e:
            logger.warning("remove_admin failed: %s", e)
            return False


def list_admins() -> list[str]:
    """
    Return list of all admin emails.
    Returns empty list if DB not configured or on error.
    """
    with _connection() as conn:
        if conn is None:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM admin_users ORDER BY email")
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.warning("list_admins failed: %s", e)
            return []


def record_query_metric(
    session_id: Optional[str] = None,
    latency_seconds: float = 0.0,
    endpoint: str = "",
    status: str = "ok",
) -> None:
    """Record a single query/request metric."""
    with _connection() as conn:
        if conn is None:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO query_metrics (session_id, endpoint, latency_seconds, status)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session_id or None, endpoint or "", latency_seconds, status or "ok"),
                )
        except Exception as e:
            logger.warning("record_query_metric failed: %s", e)


def record_feedback(
    session_id: Optional[str] = None,
    helpful: bool = False,
) -> None:
    """Record optional 'Was this helpful?' feedback."""
    with _connection() as conn:
        if conn is None:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO feedback (session_id, helpful)
                    VALUES (%s, %s)
                    """,
                    (session_id or None, helpful),
                )
        except Exception as e:
            logger.warning("record_feedback failed: %s", e)


def get_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """
    Return aggregated metrics for dashboard: query count, avg latency, feedback counts.
    date_from / date_to: optional ISO date strings (YYYY-MM-DD) to filter by created_at.
    """
    with _connection() as conn:
        if conn is None:
            return {
                "query_count": 0,
                "avg_latency_seconds": 0.0,
                "p50_latency_seconds": None,
                "p95_latency_seconds": None,
                "feedback_helpful_count": 0,
                "feedback_not_helpful_count": 0,
                "message": "Metrics DB not configured; stub only.",
            }
        try:
            with conn.cursor() as cur:
                # Build optional date filter (parameterized)
                extra = []
                params = []
                if date_from:
                    extra.append("created_at >= %s::date")
                    params.append(date_from)
                if date_to:
                    extra.append("created_at <= (%s::date + INTERVAL '1 day')")
                    params.append(date_to)
                where = (" AND " + " AND ".join(extra)) if extra else ""

                cur.execute(
                    f"""
                    SELECT COUNT(*), COALESCE(AVG(latency_seconds), 0),
                           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_seconds),
                           PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_seconds)
                    FROM query_metrics
                    WHERE 1=1 {where}
                    """,
                    tuple(params),
                )
                row = cur.fetchone()
                query_count = row[0] or 0
                avg_latency = float(row[1] or 0.0)
                p50 = float(row[2]) if row[2] is not None else None
                p95 = float(row[3]) if row[3] is not None else None

                cur.execute(
                    f"""
                    SELECT helpful, COUNT(*)
                    FROM feedback
                    WHERE 1=1 {where}
                    GROUP BY helpful
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()
                helpful_count = 0
                not_helpful_count = 0
                for helpful, cnt in rows:
                    if helpful:
                        helpful_count = cnt
                    else:
                        not_helpful_count = cnt

            return {
                "query_count": query_count,
                "avg_latency_seconds": round(avg_latency, 3),
                "p50_latency_seconds": round(p50, 3) if p50 is not None else None,
                "p95_latency_seconds": round(p95, 3) if p95 is not None else None,
                "feedback_helpful_count": helpful_count,
                "feedback_not_helpful_count": not_helpful_count,
            }
        except Exception as e:
            logger.warning("get_summary failed: %s", e)
            return {
                "query_count": 0,
                "avg_latency_seconds": 0.0,
                "p50_latency_seconds": None,
                "p95_latency_seconds": None,
                "feedback_helpful_count": 0,
                "feedback_not_helpful_count": 0,
                "error": str(e),
            }
