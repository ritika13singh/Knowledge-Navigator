"""
Metrics API — endpoints that read/write the PostgreSQL metrics collection.

Requires DATABASE_URL. Returns real aggregates when DB is configured; otherwise stub data.
"""
from __future__ import annotations
from typing import Annotated, Optional

from fastapi import APIRouter, Depends

from backend import metrics_db
from backend.auth import AuthUser, get_optional_user
from backend.schemas.metrics import FeedbackRequest

router = APIRouter(prefix="/api/metrics", tags=["metrics"])
OptionalUser = Annotated[Optional[AuthUser], Depends(get_optional_user)]


def _authenticated_flag(user: Optional[AuthUser]) -> str:
    return "yes" if user is not None else "no"


@router.get("/summary")
def metrics_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: OptionalUser = None,
):
    """
    Dashboard/report: query count, avg latency, etc.
    Stub: returns placeholder until metrics DB is connected.
    """
    data = metrics_db.get_summary(date_from=date_from, date_to=date_to)
    if isinstance(data, dict):
        data["authenticated"] = _authenticated_flag(user)
    return data


@router.post("/feedback")
def feedback(body: FeedbackRequest, user: OptionalUser = None):
    """
    Optional 'Was this helpful?' or 'Did you find what you needed?'.
    Stub: no-op until metrics DB is connected.
    """
    metrics_db.record_feedback(session_id=body.session_id, helpful=body.helpful)
    return {
        "ok": True,
        "message": "Feedback recorded.",
        "authenticated": _authenticated_flag(user),
    }
