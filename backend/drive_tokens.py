"""
Store Google refresh tokens per user (sub) for Drive API access with personal account.
In production, use a secure store (DB/vault). This in-memory store is for prototype use.
"""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# sub -> { "refresh_token": str }
_refresh_tokens: dict[str, str] = {}
_lock = None

def _get_lock():
    global _lock
    if _lock is None:
        import threading
        _lock = threading.Lock()
    return _lock


def set_refresh_token(sub: str, refresh_token: str) -> None:
    """Store refresh token for user (called after OAuth callback)."""
    if not sub or not refresh_token:
        return
    with _get_lock():
        _refresh_tokens[sub] = refresh_token


def get_refresh_token(sub: str) -> Optional[str]:
    """Return stored refresh token for user, or None."""
    with _get_lock():
        return _refresh_tokens.get(sub)


def delete_refresh_token(sub: str) -> None:
    """Remove stored refresh token (e.g. on logout)."""
    with _get_lock():
        _refresh_tokens.pop(sub, None)


def get_access_token_for_drive(sub: str) -> Optional[str]:
    """
    Return a valid Google access token with Drive scope for the user.
    Uses stored refresh_token to refresh if needed. Returns None if no token or refresh fails.
    """
    import os
    refresh_token = get_refresh_token(sub)
    if not refresh_token:
        return None
    from backend.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None
    import httpx
    try:
        r = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0,
        )
        if r.status_code != 200:
            logger.warning("Drive token refresh failed: %s %s", r.status_code, r.text[:200])
            return None
        data = r.json()
        return data.get("access_token")
    except Exception as e:
        logger.warning("Drive token refresh error: %s", e)
        return None
