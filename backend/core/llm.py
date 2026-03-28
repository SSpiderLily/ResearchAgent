from __future__ import annotations

import dashscope
from dashscope import Generation

from config import DASHSCOPE_API_KEY, LLM_MODEL

dashscope.api_key = DASHSCOPE_API_KEY


def chat_completion(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """Call Qwen LLM via DashScope and return the response text."""
    resp = Generation.call(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        result_format="message",
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"LLM API error {resp.status_code}: {resp.message}"
        )

    return resp.output.choices[0].message.content
