"""
Optional authentication: validate JWT from cookie or Authorization header.
Returns user info when authenticated, None when not (so UI works for everyone).
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Annotated, Optional

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import AUTH_COOKIE_MAX_AGE, AUTH_COOKIE_NAME, JWT_SECRET_KEY

# Algorithm for our own JWTs (signed with secret)
JWT_ALGORITHM = "HS256"


@dataclass
class AuthUser:
    """Minimal user info after Google OAuth (no PII in logs beyond necessity)."""
    sub: str          # Google subject id (stable)
    email: Optional[str]  # Optional; may be omitted in token for privacy
    name: Optional[str]
    picture: Optional[str]
    is_admin: bool = False  # True if email is in admin_users table


def _decode_token(token: str) -> Optional[AuthUser]:
    if not JWT_SECRET_KEY or not token:
        return None
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        return AuthUser(
            sub=payload["sub"],
            email=payload.get("email"),
            name=payload.get("name"),
            picture=payload.get("picture"),
            is_admin=bool(payload.get("is_admin")),
        )
    except (jwt.InvalidTokenError, KeyError):
        return None


def _token_from_request(request: Request) -> Optional[str]:
    # Prefer cookie (used by browser after OAuth callback)
    cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if cookie:
        return cookie
    # Allow Bearer for API clients
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def get_optional_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(HTTPBearer(auto_error=False))],
) -> Optional[AuthUser]:
    """
    Dependency: returns current user if authenticated, else None.
    Use this for endpoints that work for both anonymous and logged-in users.
    """
    token = _token_from_request(request)
    if not token and credentials:
        token = credentials.credentials
    return _decode_token(token) if token else None


def get_required_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(HTTPBearer(auto_error=False))],
) -> AuthUser:
    """
    Dependency: returns current user if authenticated, raises 401 if not.
    Use this for endpoints that require authentication.
    """
    from fastapi import HTTPException
    token = _token_from_request(request)
    if not token and credentials:
        token = credentials.credentials
    user = _decode_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# Type aliases for dependency injection
OptionalUser = Annotated[Optional[AuthUser], Depends(get_optional_user)]
RequiredUser = Annotated[AuthUser, Depends(get_required_user)]


def create_session_token(
    sub: str,
    email: Optional[str],
    name: Optional[str],
    picture: Optional[str],
    is_admin: bool = False,
) -> str:
    """Build JWT for session (called after successful Google OAuth)."""
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY must be set for auth")
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "picture": picture,
        "is_admin": is_admin,
        "exp": now + AUTH_COOKIE_MAX_AGE,
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
