"""Thin wrapper around the Anthropic Messages API.

Isolated in its own module so agent unit tests can monkeypatch
`complete_json` instead of hitting the network / requiring a live
ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
import re

from app.config import ANTHROPIC_API_KEY

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    fenced = _JSON_FENCE_RE.search(text)
    candidate = fenced.group(1) if fenced else text
    return json.loads(candidate)


def complete_json(system_prompt: str, user_content: str, model: str, max_tokens: int = 1024) -> dict:
    """Calls Claude with a system prompt instructing JSON-only output and
    parses the response. Raises on missing API key or malformed JSON so
    callers can decide how to handle failure (retry, fallback, etc.)."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set it in the environment to run the live "
            "LangGraph pipeline; agent unit tests mock this function instead."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_json(text)


def complete_text(system_prompt: str, user_content: str, model: str, max_tokens: int = 2048) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set it in the environment to run the live "
            "LangGraph pipeline; agent unit tests mock this function instead."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
