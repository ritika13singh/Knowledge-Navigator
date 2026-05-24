"""Health check endpoints — no auth, no metrics DB."""
from __future__ import annotations
from typing import Annotated, Optional

from fastapi import APIRouter, Depends

from backend.auth import AuthUser, get_optional_user

router = APIRouter(prefix="/api", tags=["health"])
OptionalUser = Annotated[Optional[AuthUser], Depends(get_optional_user)]


@router.get("/health")
def health(user: OptionalUser = None):
    """Health check; does not require auth."""
    return {
        "status": "ok",
        "service": "nesst-knowledge-navigator",
        "authenticated": "yes" if user is not None else "no",
    }
