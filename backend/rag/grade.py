"""LLM-as-grader: ask OpenAI whether each chunk is relevant to the question."""
from __future__ import annotations
import json
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_GRADER_MODEL

_GRADE_PROMPT = """\
You are a relevce grader. Decide whether the document chunk below contains \
information useful for answering the question.

Question: {question}

Chunk:
{chunk}

Reply with ONLY valid JSON in this exact format:
{{"relevant": true, "reason": "one short sentence"}}
or
{{"relevant": false, "reason": "one short sentence"}}"""

def _grade_one(client, question: str, chunk: str) -> tuple[bool, str]:
    try:
        response = client.chat.completions.create(
            model=OPENAI_GRADER_MODEL,
            max_tokens=128,
            messages=[{"role": "user", "content": _GRADE_PROMPT.format(
                question=question, chunk=chunk[:2000]
            )}],
        )
        text = response.choices[0].message.content or ""
        data = json.loads(text.strip())
        return bool(data.get("relevant")), str(data.get("reason", ""))
    except Exception as e:
        return True, f"grading error: {e}"

def grade_chunks(question: str, chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []
    if not OPENAI_API_KEY:
        return [{**c, "relevant": True, "grade_reason": "grading skipped"} for c in chunks]
    client = OpenAI(api_key=OPENAI_API_KEY)
    graded = []
    for chunk in chunks:
        relevant, reason = _grade_one(client, question, chunk.get("text", ""))
        graded.append({**chunk, "relevant": relevant, "grade_reason": reason})
    return graded
