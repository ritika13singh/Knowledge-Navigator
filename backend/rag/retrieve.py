"""Embed a query and retrieve the top-k chunks from ChromaDB."""
from __future__ import annotations
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
from backend.rag.chroma import get_collection

TOP_K = 5

def _embed_query(query: str) -> list[float]:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=[query])
    return resp.data[0].embedding

def retrieve(query: str, n_results: int = TOP_K) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    embedding = _embed_query(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "filename": meta.get("filename", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "distance": round(dist, 4),
        })
    return chunks
