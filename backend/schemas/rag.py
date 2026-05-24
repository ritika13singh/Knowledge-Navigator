"""Request/response models for RAG and query APIs."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class RetrieveRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None  # optional, for metrics (no PII)
    # Thematic filters
    themes: Optional[list[str]] = None
    document_type: Optional[str] = None
    date_from: Optional[str] = None  # ISO date YYYY-MM-DD
    date_to: Optional[str] = None  # ISO date YYYY-MM-DD
    internal_only: bool = False


class ChatMessage(BaseModel):
    """Single message in conversation history (role + content only)."""
    role: str  # "user" | "assistant"
    content: str


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None  # optional, for metrics (no PII)
    # Optional prior conversation for multi-turn context (last N messages)
    conversation_history: list[ChatMessage] | None = None
    # Thematic filters
    themes: Optional[list[str]] = None
    document_type: Optional[str] = None
    date_from: Optional[str] = None  # ISO date YYYY-MM-DD
    date_to: Optional[str] = None  # ISO date YYYY-MM-DD
    internal_only: bool = False
    public_mode: bool = False  # When true, restricts access to public-only content (excludes memos)


class DeleteFileRequest(BaseModel):
    file_name: str


class InsertFileRequest(BaseModel):
    """Metadata for file ingestion."""
    themes: Optional[list[str]] = None
    document_type: str = "other"
    visibility: str = "public"  # "public" or "internal"
    title: Optional[str] = None
    description: Optional[str] = None


class SourceInfo(BaseModel):
    """Source document info in response."""
    title: Optional[str] = None
    file_name: Optional[str] = None
    document_type: Optional[str] = None
    themes: list[str] = []


class QueryResponse(BaseModel):
    """Response from /api/query with thematic info."""
    answer: str
    sources_used: bool
    sources: list[SourceInfo] = []
    themes_used: list[str] = []
    latency_seconds: float | None = None
    rag_error: Optional[str] = None
