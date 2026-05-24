"""
Google OAuth: login, callback, me, logout.
Session is stored in an httpOnly cookie (JWT). Everyone can use the UI; backend
differentiates authenticated vs anonymous via optional auth.
"""
from __future__ import annotations
from typing import Optional
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

from backend.auth import create_session_token
from backend import drive_tokens
from backend.config import (
    AUTH_COOKIE_MAX_AGE,
    AUTH_COOKIE_NAME,
    FRONTEND_ORIGIN,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    JWT_SECRET_KEY,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
# Sign-in + Drive readonly for "Manage Drive" (personal account monitoring).
# For a published app, drive.readonly is a sensitive scope and may require Google verification.
SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/drive.readonly"]


def _redirect_uri(request: Request) -> str:
    """Callback URL must match exactly what is configured in Google Cloud Console."""
    base = request.base_url
    return str(base).rstrip("/") + "/api/auth/callback"


@router.get("/google")
def auth_google(request: Request):
    """
    Redirect user to Google consent screen. After login, Google redirects to
    /api/auth/callback with a code.
    """
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse(
            url=f"{FRONTEND_ORIGIN}/login?error=oauth_not_configured",
            status_code=302,
        )
    state = secrets.token_urlsafe(32)
    # Store state in cookie for CSRF check (same-site cookie)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    response = RedirectResponse(url=url, status_code=302)
    response.set_cookie(
        "oauth_state",
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return response


def _redirect_to_login(error: str) -> RedirectResponse:
    """Always return a redirect so the user never sees ERR_EMPTY_RESPONSE."""
    return RedirectResponse(url=f"{FRONTEND_ORIGIN}/login?error={error}", status_code=302)


@router.get("/callback")
async def auth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """
    Google redirects here with ?code=...&state=... or ?error=...
    Exchange code for tokens, fetch userinfo, set session cookie, redirect to frontend.
    """
    try:
        if error:
            return _redirect_to_login(error)
        if not code or not state:
            return _redirect_to_login("missing_code")
        stored_state = request.cookies.get("oauth_state")
        if not stored_state or not secrets.compare_digest(state, stored_state):
            return _redirect_to_login("invalid_state")
        if not GOOGLE_CLIENT_SECRET or not JWT_SECRET_KEY:
            return _redirect_to_login("server_config")

        redirect_uri = _redirect_uri(request)
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15.0,
            )
        if token_res.status_code != 200:
            logger.warning("Google token exchange failed: %s %s", token_res.status_code, token_res.text[:200])
            return _redirect_to_login("token_exchange")
        try:
            token_data = token_res.json()
        except Exception as e:
            logger.warning("Token response not JSON: %s", e)
            return _redirect_to_login("token_exchange")
        access_token = token_data.get("access_token")
        if not access_token:
            return _redirect_to_login("no_access_token")

        async with httpx.AsyncClient() as client:
            user_res = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
        if user_res.status_code != 200:
            logger.warning("Google userinfo failed: %s", user_res.status_code)
            return _redirect_to_login("userinfo")
        try:
            user_data = user_res.json()
        except Exception as e:
            logger.warning("Userinfo not JSON: %s", e)
            return _redirect_to_login("userinfo")
        sub = user_data.get("id") or user_data.get("sub")
        if not sub:
            return _redirect_to_login("no_user_id")
        email = user_data.get("email")
        name = user_data.get("name")
        picture = user_data.get("picture")

        # Store refresh token for Drive API (personal account monitoring).
        refresh_token = token_data.get("refresh_token")
        if refresh_token:
            drive_tokens.set_refresh_token(sub, refresh_token)

        # Check if user is admin by comparing email with admin_users table
        from backend import metrics_db
        is_admin = metrics_db.is_admin(email)

        jwt_token = create_session_token(
            sub=sub, email=email, name=name, picture=picture, is_admin=is_admin
        )
        redirect = RedirectResponse(url=f"{FRONTEND_ORIGIN}/", status_code=302)
        redirect.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=jwt_token,
            max_age=AUTH_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
            secure=request.url.scheme == "https",
        )
        redirect.delete_cookie("oauth_state", path="/")
        return redirect
    except Exception as e:
        logger.exception("OAuth callback failed: %s", e)
        return _redirect_to_login("callback_error")


@router.get("/me")
def auth_me(request: Request):
    """
    Return current user from session cookie or Bearer token. 401 if not authenticated.
    Frontend uses this to show user state and to send credentials with API calls.
    Note: is_admin is checked from DB in real-time, not from JWT token.
    """
    from backend.auth import _decode_token, _token_from_request
    from backend import metrics_db

    token = _token_from_request(request)
    user = _decode_token(token) if token else None
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check admin status from DB in real-time (not from cached JWT)
    is_admin = metrics_db.is_admin(user.email)
    
    return {
        "sub": user.sub,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "is_admin": is_admin,
        "authenticated": "yes",
    }


@router.post("/logout")
def auth_logout(request: Request):
    """Clear session cookie and Drive refresh token. Frontend redirects after calling this."""
    from fastapi.responses import JSONResponse
    from backend.auth import _decode_token, _token_from_request

    token = _token_from_request(request)
    user = _decode_token(token) if token else None
    if user:
        drive_tokens.delete_refresh_token(user.sub)

    response = JSONResponse(content={"ok": True, "authenticated": "no"})
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response
