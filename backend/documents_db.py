"""
Documents Metadata DB — PostgreSQL tables for document metadata with thematic organization.

Uses DATABASE_URL from config. If unset, all functions no-op or return stub data.
Tables: documents (file metadata with themes, document_type, visibility).
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)

TABLE_DOCUMENTS = "documents"

# Predefined themes and document types
VALID_THEMES = [
    "skills_employment",      # Workforce development, talent gaps, employment
    "social_enterprise",      # SE development, manuals, guides
    "impact_investment",      # Financing, co-investment, returns
    "case_study",             # Specific enterprise/program case studies
    "regional_report",        # Country/region specific analyses
    "annual_report",          # Organizational annual reports
    "policy_governance",      # Policy, integrity, compliance documents
    "shared_value",           # Corporate partnerships, shared value
    "innovation_research",    # Research publications, innovation
    "general",                # General/uncategorized
]

VALID_DOCUMENT_TYPES = [
    "report",
    "manual",
    "case_study",
    "policy",
    "training",
    "learning",
    "presentation",
    "template",
    "other",
]


def _get_conn():
    """Return a DB connection or None if DATABASE_URL is not set."""
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.warning("Documents DB connect failed: %s", e)
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
    Create documents table if it does not exist. Call once at app startup.
    Returns True if table was created or already exists, False if DB not configured.
    """
    with _connection() as conn:
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        file_name VARCHAR(512) NOT NULL UNIQUE,
                        doc_id VARCHAR(255),
                        themes TEXT[] DEFAULT '{}',
                        document_type VARCHAR(100) DEFAULT 'other',
                        visibility VARCHAR(50) DEFAULT 'public',
                        ingest_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        title VARCHAR(512),
                        description TEXT,
                        chunk_ids TEXT[] DEFAULT '{}'
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_documents_themes ON documents USING GIN(themes)
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type)
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_documents_visibility ON documents(visibility)
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_documents_ingest_date ON documents(ingest_date)
                    """
                )
            return True
        except Exception as e:
            logger.warning("Documents DB ensure_tables failed: %s", e)
            return False


def upsert_document(
    file_name: str,
    doc_id: Optional[str] = None,
    themes: Optional[list[str]] = None,
    document_type: str = "other",
    visibility: str = "public",
    title: Optional[str] = None,
    description: Optional[str] = None,
    chunk_ids: Optional[list[str]] = None,
) -> Optional[dict]:
    """
    Insert or update a document's metadata.
    Returns the document record or None if DB not configured.
    """
    themes = themes or []
    chunk_ids = chunk_ids or []
    
    with _connection() as conn:
        if conn is None:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (file_name, doc_id, themes, document_type, visibility, title, description, chunk_ids)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_name) DO UPDATE SET
                        doc_id = COALESCE(EXCLUDED.doc_id, documents.doc_id),
                        themes = EXCLUDED.themes,
                        document_type = EXCLUDED.document_type,
                        visibility = EXCLUDED.visibility,
                        title = COALESCE(EXCLUDED.title, documents.title),
                        description = COALESCE(EXCLUDED.description, documents.description),
                        chunk_ids = EXCLUDED.chunk_ids,
                        updated_at = NOW()
                    RETURNING id, file_name, doc_id, themes, document_type, visibility, ingest_date, updated_at, title, description, chunk_ids
                    """,
                    (file_name, doc_id, themes, document_type, visibility, title, description, chunk_ids),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "file_name": row[1],
                        "doc_id": row[2],
                        "themes": row[3] or [],
                        "document_type": row[4],
                        "visibility": row[5],
                        "ingest_date": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None,
                        "title": row[8],
                        "description": row[9],
                        "chunk_ids": row[10] or [],
                    }
                return None
        except Exception as e:
            logger.warning("upsert_document failed: %s", e)
            return None


def get_document(file_name: str) -> Optional[dict]:
    """Get a document by file_name."""
    with _connection() as conn:
        if conn is None:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, file_name, doc_id, themes, document_type, visibility, ingest_date, updated_at, title, description, chunk_ids
                    FROM documents WHERE file_name = %s
                    """,
                    (file_name,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "file_name": row[1],
                        "doc_id": row[2],
                        "themes": row[3] or [],
                        "document_type": row[4],
                        "visibility": row[5],
                        "ingest_date": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None,
                        "title": row[8],
                        "description": row[9],
                        "chunk_ids": row[10] or [],
                    }
                return None
        except Exception as e:
            logger.warning("get_document failed: %s", e)
            return None


def list_documents(
    themes: Optional[list[str]] = None,
    document_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    internal_only: bool = False,
) -> list[dict]:
    """
    List documents with optional filters.
    - themes: filter by any matching theme (OR logic)
    - document_type: exact match
    - date_from/date_to: filter by ingest_date
    - internal_only: if True, only return visibility='internal'
    """
    with _connection() as conn:
        if conn is None:
            return []
        try:
            with conn.cursor() as cur:
                conditions = ["1=1"]
                params = []
                
                if themes:
                    conditions.append("themes && %s")
                    params.append(themes)
                
                if document_type:
                    conditions.append("document_type = %s")
                    params.append(document_type)
                
                if date_from:
                    conditions.append("ingest_date >= %s::date")
                    params.append(date_from)
                
                if date_to:
                    conditions.append("ingest_date <= (%s::date + INTERVAL '1 day')")
                    params.append(date_to)
                
                if internal_only:
                    conditions.append("visibility = 'internal'")
                else:
                    conditions.append("visibility != 'internal'")
                
                where_clause = " AND ".join(conditions)
                
                cur.execute(
                    f"""
                    SELECT id, file_name, doc_id, themes, document_type, visibility, ingest_date, updated_at, title, description, chunk_ids
                    FROM documents
                    WHERE {where_clause}
                    ORDER BY ingest_date DESC
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "file_name": row[1],
                        "doc_id": row[2],
                        "themes": row[3] or [],
                        "document_type": row[4],
                        "visibility": row[5],
                        "ingest_date": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None,
                        "title": row[8],
                        "description": row[9],
                        "chunk_ids": row[10] or [],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning("list_documents failed: %s", e)
            return []


def get_file_names_by_filters(
    themes: Optional[list[str]] = None,
    document_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    internal_only: bool = False,
) -> list[str]:
    """
    Get list of file_names matching the filters.
    Used to filter RAG results by metadata.
    """
    docs = list_documents(
        themes=themes,
        document_type=document_type,
        date_from=date_from,
        date_to=date_to,
        internal_only=internal_only,
    )
    return [d["file_name"] for d in docs]


def delete_document(file_name: str) -> bool:
    """Delete a document by file_name."""
    with _connection() as conn:
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM documents WHERE file_name = %s",
                    (file_name,),
                )
                return cur.rowcount > 0
        except Exception as e:
            logger.warning("delete_document failed: %s", e)
            return False


def get_all_themes() -> list[str]:
    """Get all unique themes used across documents."""
    with _connection() as conn:
        if conn is None:
            return VALID_THEMES
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT unnest(themes) as theme FROM documents ORDER BY theme
                    """
                )
                rows = cur.fetchall()
                if rows:
                    return [row[0] for row in rows]
                return VALID_THEMES
        except Exception as e:
            logger.warning("get_all_themes failed: %s", e)
            return VALID_THEMES


def get_all_document_types() -> list[str]:
    """Get all unique document types used."""
    with _connection() as conn:
        if conn is None:
            return VALID_DOCUMENT_TYPES
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT document_type FROM documents WHERE document_type IS NOT NULL ORDER BY document_type
                    """
                )
                rows = cur.fetchall()
                if rows:
                    return [row[0] for row in rows]
                return VALID_DOCUMENT_TYPES
        except Exception as e:
            logger.warning("get_all_document_types failed: %s", e)
            return VALID_DOCUMENT_TYPES


def get_themes_summary() -> list[dict]:
    """Get theme counts for browse-by-theme UI."""
    with _connection() as conn:
        if conn is None:
            return [{"theme": t, "count": 0} for t in VALID_THEMES]
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT theme, COUNT(*) as cnt
                    FROM (SELECT unnest(themes) as theme FROM documents) sub
                    GROUP BY theme
                    ORDER BY cnt DESC, theme
                    """
                )
                rows = cur.fetchall()
                return [{"theme": row[0], "count": row[1]} for row in rows]
        except Exception as e:
            logger.warning("get_themes_summary failed: %s", e)
            return []
