"""Ingest PDF/TXT/CSV into ChromaDB: extract → chunk → embed → store."""
from __future__ import annotations
import csv, hashlib
from pathlib import Path
from typing import Any
import tiktoken
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
from backend.rag.chroma import get_collection

CHUNK_TOKENS = 512
OVERLAP_TOKENS = 128
ENCODING = "cl100k_base"

def _openai_client():
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY. Set it in .env.")
    return OpenAI(api_key=OPENAI_API_KEY)

def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".csv":
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            rows = list(csv.reader(f))
        return "\n".join(",".join(row) for row in rows)
    return path.read_text(encoding="utf-8", errors="replace")

def _chunk_text(text: str) -> list[str]:
    enc = tiktoken.get_encoding(ENCODING)
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_TOKENS, len(tokens))
        chunks.append(enc.decode(tokens[start:end]))
        if end == len(tokens):
            break
        start += CHUNK_TOKENS - OVERLAP_TOKENS
    return [c for c in chunks if c.strip()]

def _embed(texts: list[str]) -> list[list[float]]:
    client = _openai_client()
    embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i+100]
        resp = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=batch)
        embeddings.extend([item.embedding for item in resp.data])
    return embeddings

def _chunk_id(filename: str, chunk_index: int) -> str:
    return hashlib.md5(f"{filename}::{chunk_index}".encode()).hexdigest()

def ingest_file(path: Path, filename: str) -> dict[str, Any]:
    text = _extract_text(path)
    if not text.strip():
        return {"ok": False, "error": "No text extracted.", "filename": filename}
    chunks = _chunk_text(text)
    if not chunks:
        return {"ok": False, "error": "No chunks produced.", "filename": filename}
    embeddings = _embed(chunks)
    ids = [_chunk_id(filename, i) for i in range(len(chunks))]
    metadatas = [{"filename": filename, "chunk_index": i} for i in range(len(chunks))]
    collection = get_collection()
    collection.upsert(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
    return {"ok": True, "filename": filename, "chunks_indexed": len(chunks)}
