"""OpenAI chat completions client for Q&A answers."""
from backend.config import OPENAI_API_KEY, OPENAI_CHAT_MODEL


def chat_completions(
    system_content: str,
    user_content: str,
    temperature: float = 0.3,
) -> dict:
    """Generate an answer using OpenAI's Chat Completions API."""
    if not OPENAI_API_KEY:
        return {
            "status_code": 503,
            "error": "Missing OPENAI_API_KEY in environment. Set it in .env.",
            "answer": None,
        }
    try:
        from openai import OpenAI
    except ImportError:
        return {
            "status_code": 503,
            "error": "openai package not installed. Run: pip install openai",
            "answer": None,
        }

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            max_tokens=4096,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        answer = response.choices[0].message.content
        return {"answer": answer}
    except Exception as exc:
        return {"status_code": 503, "error": str(exc), "answer": None}
