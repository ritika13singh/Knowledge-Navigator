"""
RAG-based APIs: retrieve, insert, delete, clear, and end-to-end query.
Uses rag_service for retrieval/ingest and llm_client (Anthropic) for Q&A.
Records metrics when DATABASE_URL is set. Supports thematic filtering via
document metadata stored in PostgreSQL.
Optional auth: authenticated users get full responses; anonymous get same API with
authenticated: false and may get limited features (e.g. fewer sources or hints).
"""
from __future__ import annotations
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend import metrics_db, documents_db
from backend.auth import AuthUser, get_optional_user
from backend.config import ALLOWED_EXTENSIONS, PROJECT_ROOT, UPLOAD_DIR
from backend.schemas.rag import DeleteFileRequest, QueryRequest, RetrieveRequest, SourceInfo
from backend.services import llm_client, rag_service

router = APIRouter(prefix="/api", tags=["rag"])
OptionalUser = Annotated[Optional[AuthUser], Depends(get_optional_user)]
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data" / "documents"

_ingest_lock = threading.Lock()
_ingest_state: dict = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "total": 0,
    "processed": 0,
    "current_file": None,
    "results": [],
    "last_error": None,
}


def _authenticated_flag(user: Optional[AuthUser]) -> str:
    """Return "yes" or "no" for API response."""
    return "yes" if user is not None else "no"


def _chunks_from_retrieved(retrieved: dict) -> list:
    """Normalize RAG response to a list of chunks."""
    chunks = (
        retrieved.get("retrieved")
        or retrieved.get("chunks")
        or retrieved.get("results")
        or retrieved.get("documents")
        or retrieved.get("contexts")
        or []
    )
    return chunks if isinstance(chunks, list) else []


def _context_from_chunks(chunks: list) -> str:
    """Build context string from chunk list (multiple key names supported)."""
    if not chunks:
        return ""
    parts = []
    for c in chunks[:20]:
        if isinstance(c, dict):
            part = (
                c.get("text")
                or c.get("content")
                or c.get("page_content")
                or c.get("body")
                or c.get("snippet")
                or c.get("chunk")
            )
            if part is None and c:
                part = next((v for v in c.values() if isinstance(v, str)), None)
            if part:
                parts.append(part)
        elif isinstance(c, str):
            parts.append(c)
    return "\n\n".join(parts)


def _source_names_from_chunks(chunks: list) -> list[str]:
    """Return unique document names (title/filename/url) from chunks used for context."""
    if not chunks:
        return []
    seen: set[str] = set()
    names: list[str] = []
    for c in chunks[:20]:
        if not isinstance(c, dict):
            continue
        name = (
            c.get("title")
            or c.get("filename")
            or c.get("url")
            or c.get("source")
            or c.get("document_name")
        )
        if name and isinstance(name, str) and name.strip() and name not in seen:
            seen.add(name)
            names.append(name.strip())
    return names


def _get_source_info_from_chunks(chunks: list) -> tuple[list[SourceInfo], list[str]]:
    """
    Extract source info with metadata from chunks.
    Returns (sources, themes_used) where sources includes document metadata.
    """
    if not chunks:
        return [], []
    
    seen_files: set[str] = set()
    sources: list[SourceInfo] = []
    all_themes: set[str] = set()
    
    for c in chunks[:20]:
        if not isinstance(c, dict):
            continue
        file_name = (
            c.get("filename")
            or c.get("source")
            or c.get("document_name")
            or c.get("title")
            or c.get("url")
        )
        if not file_name or not isinstance(file_name, str) or file_name in seen_files:
            continue
        seen_files.add(file_name)
        
        # Look up metadata from documents DB
        doc_meta = documents_db.get_document(file_name)
        if doc_meta:
            sources.append(SourceInfo(
                title=doc_meta.get("title") or file_name,
                file_name=file_name,
                document_type=doc_meta.get("document_type"),
                themes=doc_meta.get("themes", []),
            ))
            for theme in doc_meta.get("themes", []):
                all_themes.add(theme)
        else:
            sources.append(SourceInfo(
                title=file_name,
                file_name=file_name,
                document_type=None,
                themes=[],
            ))
    
    return sources, list(all_themes)


def _filter_chunks_by_metadata(
    chunks: list,
    themes: Optional[list[str]] = None,
    document_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    internal_only: bool = False,
    public_mode: bool = False,
) -> list:
    """
    Filter RAG chunks by document metadata.
    If no filters are set, returns all chunks.
    When public_mode is True, excludes memo documents (internal only).
    """
    if not any([themes, document_type, date_from, date_to, internal_only, public_mode]):
        return chunks
    
    # Get allowed file names from metadata DB
    allowed_files = set(documents_db.get_file_names_by_filters(
        themes=themes,
        document_type=document_type,
        date_from=date_from,
        date_to=date_to,
        internal_only=internal_only,
    ))
    
    if not allowed_files:
        # No documents in DB match the filters. Don't drop RAG chunks—they may be from
        # files not in our metadata or from a different source; return chunks unfiltered.
        return chunks
    
    filtered = []
    for c in chunks:
        if not isinstance(c, dict):
            continue
        file_name = (
            c.get("filename")
            or c.get("file_name")
            or c.get("source")
            or c.get("document_name")
            or c.get("title")
        )
        
        # In public mode, exclude memo documents even if not in DB
        if public_mode and file_name:
            # Check if this is a memo document (by filename or metadata)
            doc_meta = documents_db.get_document(file_name)
            if doc_meta and doc_meta.get("document_type", "").lower() == "memo":
                continue  # Skip memo documents in public mode
            # Also check filename for memo indicators
            if "memo" in file_name.lower():
                continue
        
        if file_name and file_name in allowed_files:
            filtered.append(c)
    
    return filtered if filtered else chunks  # Fallback to all if no matches


@router.post("/rag/retrieve")
def rag_retrieve(body: RetrieveRequest, user: OptionalUser = None):
    """
    RAG retrieve: natural-language prompt → relevant chunks from ingested docs.
    Retrieves relevant chunks from the RAG index.
    Supports optional thematic filters: themes, document_type, date_from, date_to, internal_only.
    """
    start = time.perf_counter()
    out = rag_service.retrieve(body.prompt)
    
    # Apply thematic filtering if any filters are set
    chunks = _chunks_from_retrieved(out)
    if chunks:
        filtered_chunks = _filter_chunks_by_metadata(
            chunks,
            themes=body.themes,
            document_type=body.document_type,
            date_from=body.date_from,
            date_to=body.date_to,
            internal_only=body.internal_only,
        )
        # Replace chunks in output with filtered ones
        for key in ("retrieved", "chunks", "results", "documents", "contexts"):
            if key in out:
                out[key] = filtered_chunks
                break
        
        # Add source info with metadata
        sources, themes_used = _get_source_info_from_chunks(filtered_chunks)
        out["sources"] = [s.model_dump() for s in sources]
        out["themes_used"] = themes_used
    
    latency = round(time.perf_counter() - start, 3)
    out["latency_seconds"] = latency
    out["authenticated"] = _authenticated_flag(user)
    status = "ok" if (out.get("status_code") or 200) == 200 else "error"
    metrics_db.record_query_metric(
        session_id=body.session_id,
        latency_seconds=latency,
        endpoint="/api/rag/retrieve",
        status=status,
    )
    return out


@router.get("/rag/retrieve/test")
def rag_retrieve_test(user: OptionalUser = None):
    """
    Quick test: run a fixed retrieve and return chunk count + first snippet.
    """
    out = rag_service.retrieve("What is Knowledge Navigator commitment to integrity?")
    chunks = _chunks_from_retrieved(out)
    first_content = ""
    if chunks and isinstance(chunks[0], dict):
        first_content = (chunks[0].get("content") or chunks[0].get("text") or "")[:400]
    return {
        "ok": out.get("status_code") is None or out.get("status_code") == 200,
        "status_code": out.get("status_code"),
        "chunk_count": len(chunks),
        "first_snippet": first_content,
        "hint": "If chunk_count is 0, restart the server and try again.",
        "authenticated": _authenticated_flag(user),
    }


@router.post("/rag/clear")
def rag_clear(user: OptionalUser = None):
    """Try to clear the RAG index."""
    result = rag_service.clear_index()
    if isinstance(result, dict):
        result["authenticated"] = _authenticated_flag(user)
    return result


@router.post("/rag/ingest/data-dir")
def rag_ingest_data_dir(user: OptionalUser = None):
    """
    Trigger on-demand ingestion of all PDF/TXT/CSV files in data/documents/.
    Files already in ChromaDB are skipped. Returns immediately; poll
    GET /api/rag/ingest/status for live progress.
    """
    with _ingest_lock:
        if _ingest_state["running"]:
            raise HTTPException(409, detail="Ingest already running. Check /api/rag/ingest/status.")
        files = sorted([
            p for p in DATA_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
        ]) if DATA_DIR.exists() else []
        _ingest_state.update({
            "running": True,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "total": len(files),
            "processed": 0,
            "current_file": None,
            "results": [],
            "last_error": None,
        })

    def _run(file_list):
        try:
            from backend.rag.chroma import get_collection
            from backend.rag.ingest import ingest_file
            collection = get_collection()
        except Exception as e:
            with _ingest_lock:
                _ingest_state["last_error"] = str(e)
                _ingest_state["running"] = False
                _ingest_state["finished_at"] = datetime.now(timezone.utc).isoformat()
            return

        for path in file_list:
            with _ingest_lock:
                _ingest_state["current_file"] = path.name
            try:
                existing = collection.get(where={"filename": path.name})
                if existing.get("ids"):
                    with _ingest_lock:
                        _ingest_state["results"].append({"filename": path.name, "status": "skipped", "chunks": len(existing["ids"])})
                        _ingest_state["processed"] += 1
                    continue
                result = ingest_file(path, path.name)
                with _ingest_lock:
                    if result.get("ok"):
                        _ingest_state["results"].append({"filename": path.name, "status": "ok", "chunks": result.get("chunks_indexed", 0)})
                    else:
                        _ingest_state["results"].append({"filename": path.name, "status": "error", "chunks": 0, "error": result.get("error", "unknown")})
                    _ingest_state["processed"] += 1
            except Exception as e:
                with _ingest_lock:
                    _ingest_state["results"].append({"filename": path.name, "status": "error", "chunks": 0, "error": str(e)})
                    _ingest_state["processed"] += 1

        with _ingest_lock:
            _ingest_state["running"] = False
            _ingest_state["current_file"] = None
            _ingest_state["finished_at"] = datetime.now(timezone.utc).isoformat()

    threading.Thread(target=_run, args=(files,), daemon=True).start()
    return {
        "status": "started",
        "total": len(files),
        "message": f"Ingesting {len(files)} file(s) from data/documents/. Poll GET /api/rag/ingest/status for progress.",
        "authenticated": _authenticated_flag(user),
    }


@router.get("/rag/ingest/status")
def rag_ingest_status():
    """Return the current state of the data-dir ingest job."""
    with _ingest_lock:
        return dict(_ingest_state)


@router.post("/rag/delete/file")
def rag_delete_file(body: DeleteFileRequest, user: OptionalUser = None):
    """Delete one file from the RAG index by name."""
    result = rag_service.delete_file(body.file_name)
    if isinstance(result, dict):
        result["authenticated"] = _authenticated_flag(user)
    return result


@router.post("/rag/insert/file")
async def rag_insert_file(
    file: UploadFile = File(...),
    themes: Optional[str] = Form(None),
    document_type: Optional[str] = Form("other"),
    visibility: Optional[str] = Form("public"),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user: OptionalUser = None,
):
    """
    RAG insert: upload a file (PDF, TXT, CSV) for ingestion.
    Optionally provide metadata: themes (comma-separated), document_type, visibility, title, description.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            detail=f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}. Got: {suffix or 'unknown'}",
        )
    contents = await file.read()
    path = UPLOAD_DIR / (file.filename or "upload")
    path.write_bytes(contents)
    try:
        result = rag_service.insert_file(path, file.filename or "upload")
        
        # Store document metadata
        theme_list = [t.strip() for t in (themes or "").split(",") if t.strip()]
        doc_meta = documents_db.upsert_document(
            file_name=file.filename or "upload",
            themes=theme_list if theme_list else ["general"],
            document_type=document_type or "other",
            visibility=visibility or "public",
            title=title or file.filename,
            description=description,
        )
        if doc_meta:
            result["document_metadata"] = doc_meta
        
        if isinstance(result, dict):
            result["authenticated"] = _authenticated_flag(user)
        return result
    finally:
        if path.exists():
            path.unlink(missing_ok=True)


@router.post("/query")
def query(body: QueryRequest, user: OptionalUser = None):
    """
    End-to-end Q&A: question → RAG retrieve → LLM with context → actionable answer.
    Supports optional conversation_history for multi-turn context; optional thematic filters.
    Response includes themes_used and enriched source info.
    Authenticated users get full sources and richer responses; anonymous get
    the same answer with authenticated: false (and optionally limited source list).
    """
    start = time.perf_counter()
    retrieved = rag_service.retrieve(body.question)
    rag_path = retrieved.get("path", "unknown")
    rag_meta = {
        "rag_path": rag_path,
        "chunks_retrieved": retrieved.get("chunks_retrieved", 0),
        "chunks_relevant": retrieved.get("chunks_relevant", 0),
    }
    if retrieved.get("rewritten_query"):
        rag_meta["rewritten_query"] = retrieved["rewritten_query"]
    chunks = _chunks_from_retrieved(retrieved)
    num_before_filter = len(chunks)
    is_authenticated = user is not None
    
    # Apply thematic filtering (and public mode restrictions)
    if chunks:
        chunks = _filter_chunks_by_metadata(
            chunks,
            themes=body.themes,
            document_type=body.document_type,
            date_from=body.date_from,
            date_to=body.date_to,
            internal_only=body.internal_only,
            public_mode=body.public_mode,
        )

    if not chunks:
        # Check for direct string response from RAG backend
        for key in ("context", "response", "content", "data"):
            if isinstance(retrieved.get(key), str):
                context = retrieved[key]
                break
        else:
            context = ""
    else:
        context = _context_from_chunks(chunks)

    if not context.strip():
        rag_error = retrieved.get("error", "")
        if isinstance(rag_error, str) and len(rag_error) > 500:
            rag_error = rag_error[:500] + "..."
        status_code = int(retrieved.get("status_code", 0) or 0)
        # Always log when we return no context so the terminal shows why (service error vs no results)
        # print() ensures visibility when logging isn't configured (uvicorn terminal)
        err_preview = (rag_error or "(empty)")[:200]
        logger.info(
            "RAG retrieve no context: status_code=%s question_len=%d error_preview=%s",
            status_code or "(none)",
            len(body.question),
            err_preview,
        )
        print(f"[Knowledge Navigator RAG] No context: status_code={status_code or '(none)'} error_preview={err_preview!r}")
        # When service returned 200, show why we have no context (filter dropped all vs wrong chunk shape)
        if not status_code:
            keys = list(retrieved.keys()) if isinstance(retrieved, dict) else []
            parts = [f"response_keys={keys!r}", f"chunks_before_filter={num_before_filter}"]
            if num_before_filter > 0:
                parts.append("chunks_after_filter=0 → all chunks removed by thematic filter or chunk keys not in metadata DB")
            for k in ("retrieved", "chunks", "results", "documents", "contexts", "context", "response", "content", "data"):
                v = retrieved.get(k) if isinstance(retrieved, dict) else None
                if v is not None:
                    if isinstance(v, list):
                        parts.append(f"{k}_len={len(v)}")
                    elif isinstance(v, str):
                        parts.append(f"{k}_str_len={len(v)}")
                    else:
                        parts.append(f"{k}={type(v).__name__}")
            print(f"[Knowledge Navigator RAG] {', '.join(parts)}")
        if status_code == 503:
            answer_msg = "The knowledge service is unreachable. Check your configuration and try again."
            if rag_error:
                answer_msg += f" ({rag_error[:200]})"
        else:
            hint = ""
            if status_code != 200:
                hint = (
                    " The search service is temporarily unavailable or returned an error; "
                    "please try again in a moment."
                )
                if status_code:
                    hint += f" (HTTP {status_code})"
                if rag_error and "query" in rag_error.lower():
                    hint = " The search API reported an issue with the request. Try rephrasing your question."
            answer_msg = (
                "No relevant documents were found for this question. Try rephrasing or ingesting more content via Upload."
                + hint
            )
            if rag_error and status_code != 200:
                answer_msg += f" (Error: {rag_error[:200]})"
        # CRAG fallback: answer from Claude's general knowledge with disclaimer
        if rag_path == "fallback":
            system_content = (
                "You are the Knowledge Navigator. No relevant documents were found in the knowledge base "
                "for this question. Answer from your general knowledge about impact investing, social enterprises, "
                "and nonprofit management, but clearly note that your answer is not sourced from Knowledge Navigator documents."
            )
            user_content = f"Question: {body.question}"
            chat_out = llm_client.chat_completions(system_content, user_content)
            answer = chat_out.get("answer") or chat_out.get("error") or "No answer generated."
            latency = round(time.perf_counter() - start, 3)
            metrics_db.record_query_metric(
                session_id=body.session_id,
                latency_seconds=latency,
                endpoint="/api/query",
                status="ok",
            )
            sources, themes_used = _get_source_info_from_chunks(chunks)
            return {
                "answer": answer,
                "sources_used": False,
                "sources": [s.model_dump() for s in sources],
                "themes_used": themes_used,
                "latency_seconds": latency,
                "authenticated": _authenticated_flag(user),
                **rag_meta,
            }
        latency = round(time.perf_counter() - start, 3)
        metrics_db.record_query_metric(
            session_id=body.session_id,
            latency_seconds=latency,
            endpoint="/api/query",
            status="ok",
        )
        sources, themes_used = _get_source_info_from_chunks(chunks)
        return {
            "answer": answer_msg,
            "sources_used": False,
            "sources": [s.model_dump() for s in sources],
            "themes_used": themes_used,
            "latency_seconds": latency,
            "rag_error": rag_error if retrieved.get("status_code") else None,
            "rag_status_code": status_code if status_code else None,
            "authenticated": _authenticated_flag(user),
            **rag_meta,
        }

    # Build filter context for the LLM
    filter_instructions = ""
    if body.themes and len(body.themes) > 0:
        theme_names = ", ".join(body.themes)
        filter_instructions += f"Focus specifically on content related to these themes: {theme_names}. "
    if body.document_type:
        filter_instructions += f"Prioritize information from {body.document_type} documents. "
    if body.internal_only:
        filter_instructions += "Focus on internal organizational content. "
    
    system_content = (
        "You are the Knowledge Navigator. You have access to document excerpts about Knowledge Navigator in the user message; use them as your source of truth for what Knowledge Navigator is and what the organization has done. "
        "Do not invent facts about the organization's past work, outcomes, or history—those must come only from the excerpts. "
         + filter_instructions +
        "When the user asks a factual question, summarize from the excerpts and stay strictly grounded. "
        "When the user asks for new ideas, ways to build on progress, creative suggestions, or 'what could we do next': (1) First briefly summarize what the excerpts say about the organization's work and progress so far. (2) Then, building only on that, suggest additional ideas or next steps that logically extend the work described. You may be creative in proposing future directions and ideas as long as they are clearly built on the context from the excerpts; do not invent past facts. Use clear paragraphs or bullet points but do not use fixed section headings like 'What the material shows' or 'Ideas to build on this'; vary your phrasing naturally. "
        "If the excerpts contain recommendations, learnings, or outcomes, you may also derive those and present them as action items or insights. "
        "If the user message includes a 'Previous conversation' section, use it to interpret the current question (e.g. follow-ups like 'tell me more', 'what about in Brazil?', 'expand on that'). "
        "Only when the excerpts truly contain nothing relevant to the question, respond with: 'The provided documents do not contain information about this.' "
        "Otherwise give a useful answer: grounded in the material for facts, and when asked for ideas, add reasoned suggestions that extend from it."
    )
    # Optional multi-turn context: last N messages, truncated to avoid blowing context window
    conversation_block = ""
    if body.conversation_history and len(body.conversation_history) > 0:
        max_turns = 10  # last 10 messages (5 exchanges)
        max_chars_per_msg = 400
        max_conversation_chars = 2500
        history = body.conversation_history[-max_turns:]
        lines = []
        total = 0
        for m in history:
            role = "User" if (m.role or "").lower() == "user" else "Assistant"
            content = (m.content or "").strip()
            if len(content) > max_chars_per_msg:
                content = content[: max_chars_per_msg - 3] + "..."
            line = f"{role}: {content}"
            if total + len(line) + 1 > max_conversation_chars:
                break
            lines.append(line)
            total += len(line) + 1
        if lines:
            conversation_block = "\n\nPrevious conversation:\n" + "\n".join(lines) + "\n\n"
    user_content = f"Document excerpts about Knowledge Navigator (use for facts and as basis for any ideas):\n\n{context[:12000]}\n\n{conversation_block}Current question: {body.question}"
    chat_out = llm_client.chat_completions(system_content, user_content, temperature=0.3)
    answer = chat_out.get("answer") or chat_out.get("error") or "No answer generated."
    latency = round(time.perf_counter() - start, 3)
    status = "ok" if not chat_out.get("status_code") or chat_out.get("status_code") == 200 else "error"
    metrics_db.record_query_metric(
        session_id=body.session_id,
        latency_seconds=latency,
        endpoint="/api/query",
        status=status,
    )
    sources, themes_used = _get_source_info_from_chunks(chunks)
    
    # Include applied filters in response
    applied_filters = {}
    if body.themes:
        applied_filters["themes"] = body.themes
    if body.document_type:
        applied_filters["document_type"] = body.document_type
    if body.date_from:
        applied_filters["date_from"] = body.date_from
    if body.date_to:
        applied_filters["date_to"] = body.date_to
    if body.internal_only:
        applied_filters["internal_only"] = body.internal_only
    
    # Authenticated users get full source list; anonymous get first 5 as hint
    if not is_authenticated and len(sources) > 5:
        sources = sources[:5]
    
    return {
        "answer": answer,
        "sources_used": True,
        "sources": [s.model_dump() for s in sources],
        "themes_used": themes_used,
        "applied_filters": applied_filters if applied_filters else None,
        "latency_seconds": latency,
        "authenticated": _authenticated_flag(user),
        **rag_meta,
    }


# --- Document Metadata Management APIs ---

@router.get("/documents")
def list_documents(
    themes: Optional[str] = None,
    document_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    internal_only: bool = False,
):
    """
    List all documents with optional filters.
    themes: comma-separated list of themes (OR logic)
    """
    theme_list = [t.strip() for t in (themes or "").split(",") if t.strip()] or None
    docs = documents_db.list_documents(
        themes=theme_list,
        document_type=document_type,
        date_from=date_from,
        date_to=date_to,
        internal_only=internal_only,
    )
    return {"documents": docs, "count": len(docs)}


@router.get("/documents/{file_name:path}")
def get_document(file_name: str):
    """Get a single document's metadata by file_name."""
    doc = documents_db.get_document(file_name)
    if not doc:
        raise HTTPException(404, detail=f"Document not found: {file_name}")
    return doc


@router.put("/documents/{file_name:path}")
def update_document(
    file_name: str,
    themes: Optional[str] = None,
    document_type: Optional[str] = None,
    visibility: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
):
    """Update a document's metadata."""
    existing = documents_db.get_document(file_name)
    if not existing:
        raise HTTPException(404, detail=f"Document not found: {file_name}")
    
    theme_list = [t.strip() for t in (themes or "").split(",") if t.strip()] if themes else existing.get("themes", [])
    doc = documents_db.upsert_document(
        file_name=file_name,
        themes=theme_list,
        document_type=document_type or existing.get("document_type", "other"),
        visibility=visibility or existing.get("visibility", "public"),
        title=title or existing.get("title"),
        description=description or existing.get("description"),
    )
    return doc


@router.delete("/documents/{file_name:path}")
def delete_document_metadata(file_name: str):
    """Delete a document's metadata (does not delete from RAG index)."""
    deleted = documents_db.delete_document(file_name)
    if not deleted:
        raise HTTPException(404, detail=f"Document not found: {file_name}")
    return {"deleted": True, "file_name": file_name}


@router.get("/themes")
def get_themes():
    """Get all available themes with document counts."""
    summary = documents_db.get_themes_summary()
    all_themes = documents_db.get_all_themes()
    return {
        "themes": all_themes,
        "summary": summary,
        "valid_themes": documents_db.VALID_THEMES,
    }


@router.get("/document-types")
def get_document_types():
    """Get all available document types."""
    types = documents_db.get_all_document_types()
    return {
        "document_types": types,
        "valid_types": documents_db.VALID_DOCUMENT_TYPES,
    }
