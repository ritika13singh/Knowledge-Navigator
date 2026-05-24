#!/usr/bin/env python3
"""Quick test of Anthropic LLM integration. Requires ANTHROPIC_API_KEY in .env."""
import dotenv

dotenv.load_dotenv()

from backend.services import llm_client

result = llm_client.chat_completions(
    system_content="You are a helpful assistant for the Knowledge Navigator.",
    user_content="In one sentence, what is impact investing?",
    temperature=0.3,
)

if result.get("answer"):
    print(result["answer"])
else:
    print("Error:", result.get("error"))
