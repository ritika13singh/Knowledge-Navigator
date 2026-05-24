"""CRAG orchestrator: retrieve → grade → rewrite+retry → fallback."""
from __future__ import annotations
from backend.rag.grade import grade_chunks
from backend.rag.retrieve import retrieve
from backend.rag.rewrite import rewrite_query

def crag_retrieve(question: str) -> dict:
    # Step 1: initial retrieval
    chunks = retrieve(question)
    chunks_retrieved = len(chunks)

    # Step 2: grade
    graded = grade_chunks(question, chunks)
    relevant = [c for c in graded if c.get("relevant")]

    if relevant:
        return {
            "retrieved": relevant,
            "path": "direct",
            "chunks_retrieved": chunks_retrieved,
            "chunks_relevant": len(relevant),
        }

    # Step 3: rewrite + second retrieval
    rewritten = rewrite_query(question)
    chunks2 = retrieve(rewritten)
    chunks_retrieved += len(chunks2)
    graded2 = grade_chunks(question, chunks2)
    relevant2 = [c for c in graded2 if c.get("relevant")]

    if relevant2:
        return {
            "retrieved": relevant2,
            "path": "rewritten",
            "rewritten_query": rewritten,
            "chunks_retrieved": chunks_retrieved,
            "chunks_relevant": len(relevant2),
        }

    # Step 4: fallback
    return {
        "retrieved": [],
        "path": "fallback",
        "rewritten_query": rewritten,
        "chunks_retrieved": chunks_retrieved,
        "chunks_relevant": 0,
    }
