"""LLM query rewriter: rephrase a question into a better vector search query."""
from __future__ import annotations
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_GRADER_MODEL

_REWRITE_PROMPT = """\
You are a search query optimizer for a document retrieval system.

Rewrite the following question into a concise, keyword-rich search query \
that will find the most relevant text chunks in an institutional knowledge base \
about impact investing, social enterprises, and nonofit management.

Original question: {question}

Reply with ONLY the rewritten query — no explanation, no quotes."""

def rewrite_query(question: str) -> str:
    if not OPENAI_API_KEY:
        return question
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_GRADER_MODEL,
            max_tokens=128,
            messages=[{"role": "user", "content": _REWRITE_PROMPT.format(question=question)}],
        )
        rewritten = response.choices[0].message.content or ""
        return rewritten.strip() or question
    except Exception:
        return question
