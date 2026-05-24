"""Request/response models for metrics API."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    helpful: bool
    session_id: Optional[str] = None
