"""Thin wrapper over the local CRAG RAG layer (backend/rag/)."""
from __future__ import annotations
from pathlib import Path
from typing import Any

def retrieve(prompt: str) -> dict[str, Any]:
    from backend.rag.crag import crag_retrieve
    try:
        return crag_retrieve(prompt)
    except Exception as e:
        return {"retrieved": [], "path": "error", "error": str(e)}

def insert_file(file_path: Path, file_name: str) -> dict[str, Any]:
    from backend.rag.ingest import ingest_file
    try:
        return ingest_file(file_path, file_name)
    except Exception as e:
        return {"ok": False, "error": str(e), "filename": file_name}

def delete_file(file_name: str) -> dict[str, Any]:
    from backend.rag.chroma import get_collection
    try:
        collection = get_collection()
        results = collection.get(where={"filename": file_name})
        ids = results.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        return {"ok": True, "file_name": file_name, "chunks_deleted": len(ids)}
    except Exception as e:
        return {"ok": False, "file_name": file_name, "error": str(e)}

def clear_index() -> dict[str, Any]:
    from backend.rag.chroma import COLLECTION_NAME, get_collection
    try:
        collection = get_collection()
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)
        return {"ok": True, "message": f"Cleared {len(all_ids)} chunks from '{COLLECTION_NAME}'."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
