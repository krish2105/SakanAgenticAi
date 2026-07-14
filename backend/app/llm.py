"""Thin wrapper around whichever LLM provider is configured.

Isolated in its own module so agent unit tests can monkeypatch
`complete_json` instead of hitting the network / requiring a live API key.

Two providers are supported, dispatched by the `model` argument's prefix
(callers never choose a provider directly -- they pass QUERY_MODEL/
REASONING_MODEL from app/config.py, whose *names* already encode which
provider they belong to):

- "claude-*"  -> Anthropic Messages API, requires ANTHROPIC_API_KEY.
- "gemini-*"  -> Google Gemini API, requires GEMINI_API_KEY. Google AI
  Studio's free tier (no credit card) is generous enough to run this whole
  pipeline for a pilot -- see app/config.py's docstring comment.

Both raise RuntimeError on a missing/wrong-provider key so every calling
agent's existing try/except deterministic-fallback path handles this
exactly like it already handles "no LLM configured at all".
"""
from __future__ import annotations

import json
import re

from app.config import ANTHROPIC_API_KEY, GEMINI_API_KEY

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    fenced = _JSON_FENCE_RE.search(text)
    candidate = fenced.group(1) if fenced else text
    return json.loads(candidate)


def _require_key(model: str, key: str | None, env_var: str) -> None:
    if not key:
        raise RuntimeError(
            f"{env_var} is not set, but model {model!r} requires it. Set it in the "
            "environment to run the live LangGraph pipeline; agent unit tests mock "
            "this function instead."
        )


def _anthropic_complete(system_prompt: str, user_content: str, model: str, max_tokens: int) -> str:
    _require_key(model, ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY")

    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _gemini_complete(system_prompt: str, user_content: str, model: str, max_tokens: int, json_mode: bool) -> str:
    _require_key(model, GEMINI_API_KEY, "GEMINI_API_KEY")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=max_tokens,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    response = client.models.generate_content(model=model, contents=user_content, config=config)
    return response.text or ""


def _dispatch(model: str, system_prompt: str, user_content: str, max_tokens: int, json_mode: bool) -> str:
    if model.startswith("gemini"):
        return _gemini_complete(system_prompt, user_content, model, max_tokens, json_mode)
    # Default to Anthropic for anything else (including unrecognized model
    # names) -- preserves prior behavior for existing "claude-*" callers.
    return _anthropic_complete(system_prompt, user_content, model, max_tokens)


def complete_json(system_prompt: str, user_content: str, model: str, max_tokens: int = 1024) -> dict:
    """Calls the model whose provider `model`'s name identifies, instructing
    JSON-only output, and parses the response. Raises on a missing/wrong
    provider key or malformed JSON so callers can decide how to handle
    failure (retry, fallback, etc.)."""
    text = _dispatch(model, system_prompt, user_content, max_tokens, json_mode=True)
    return _extract_json(text)


def complete_text(system_prompt: str, user_content: str, model: str, max_tokens: int = 2048) -> str:
    return _dispatch(model, system_prompt, user_content, max_tokens, json_mode=False)
