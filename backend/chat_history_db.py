"""
Chat History DB — PostgreSQL table for persisting user chat conversations.

Uses DATABASE_URL from config. If unset, all functions no-op or return empty data.
Table: chat_conversations (stores conversations per user).
"""
from __future__ import annotations
from typing import Optional

import json
import logging
from contextlib import contextmanager
from datetime import datetime

from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)

TABLE_CHAT_CONVERSATIONS = "chat_conversations"


def _get_conn():
    """Return a DB connection or None if DATABASE_URL is not set."""
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.warning("Chat History DB connect failed: %s", e)
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
    Create chat history table if it does not exist. Call once at app startup.
    Returns True if table was created or already exists, False if DB not configured.
    """
    with _connection() as conn:
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {TABLE_CHAT_CONVERSATIONS} (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        conversation_id VARCHAR(255) NOT NULL,
                        title VARCHAR(500) NOT NULL DEFAULT 'New chat',
                        messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(user_id, conversation_id)
                    )
                    """
                )
                # Create index for faster user lookups
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_id 
                    ON {TABLE_CHAT_CONVERSATIONS} (user_id, updated_at DESC)
                    """
                )
            return True
        except Exception as e:
            logger.warning("Chat History DB ensure_tables failed: %s", e)
            return False


def get_user_conversations(user_id: str, limit: int = 50) -> list[dict]:
    """
    Get all conversations for a user, ordered by most recently updated.
    Returns list of conversation metadata (id, title, created_at, updated_at).
    """
    with _connection() as conn:
        if conn is None:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT conversation_id, title, messages, created_at, updated_at
                    FROM {TABLE_CHAT_CONVERSATIONS}
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "messages": row[2] if isinstance(row[2], list) else json.loads(row[2]) if row[2] else [],
                        "createdAt": row[3].isoformat() if row[3] else None,
                        "updatedAt": row[4].isoformat() if row[4] else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning("get_user_conversations failed: %s", e)
            return []


def get_conversation(user_id: str, conversation_id: str) -> Optional[dict]:
    """
    Get a specific conversation for a user.
    Returns conversation dict or None if not found.
    """
    with _connection() as conn:
        if conn is None:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT conversation_id, title, messages, created_at, updated_at
                    FROM {TABLE_CHAT_CONVERSATIONS}
                    WHERE user_id = %s AND conversation_id = %s
                    """,
                    (user_id, conversation_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "title": row[1],
                    "messages": row[2] if isinstance(row[2], list) else json.loads(row[2]) if row[2] else [],
                    "createdAt": row[3].isoformat() if row[3] else None,
                    "updatedAt": row[4].isoformat() if row[4] else None,
                }
        except Exception as e:
            logger.warning("get_conversation failed: %s", e)
            return None


def save_conversation(
    user_id: str,
    conversation_id: str,
    title: str,
    messages: list[dict],
) -> bool:
    """
    Save or update a conversation for a user.
    Uses upsert (INSERT ... ON CONFLICT UPDATE).
    Returns True on success, False on failure.
    """
    with _connection() as conn:
        if conn is None:
            return True  # no DB configured — silent no-op
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {TABLE_CHAT_CONVERSATIONS} (user_id, conversation_id, title, messages, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, NOW())
                    ON CONFLICT (user_id, conversation_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        messages = EXCLUDED.messages,
                        updated_at = NOW()
                    """,
                    (user_id, conversation_id, title, json.dumps(messages)),
                )
            return True
        except Exception as e:
            logger.warning("save_conversation failed: %s", e)
            return False


def delete_conversation(user_id: str, conversation_id: str) -> bool:
    """
    Delete a conversation for a user.
    Returns True on success, False on failure.
    """
    with _connection() as conn:
        if conn is None:
            return True  # no DB configured — silent no-op
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    DELETE FROM {TABLE_CHAT_CONVERSATIONS}
                    WHERE user_id = %s AND conversation_id = %s
                    """,
                    (user_id, conversation_id),
                )
            return True
        except Exception as e:
            logger.warning("delete_conversation failed: %s", e)
            return False
