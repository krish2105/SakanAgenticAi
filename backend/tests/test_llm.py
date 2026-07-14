"""Provider-dispatch tests for app/llm.py: which SDK gets called for which
model prefix, and that a missing/wrong key raises the same RuntimeError
shape every agent's fallback path already expects."""
import pytest

import app.llm as llm_module


class _FakeAnthropicResponse:
    def __init__(self, text: str):
        self.content = [type("Block", (), {"type": "text", "text": text})()]


class _FakeAnthropicMessages:
    def __init__(self, captured: dict):
        self._captured = captured

    def create(self, **kwargs):
        self._captured.update(kwargs)
        return _FakeAnthropicResponse('{"ok": true}')


class _FakeAnthropicClient:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.messages = _FakeAnthropicMessages(_LAST_CALL)


class _FakeGeminiResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeGeminiModels:
    def generate_content(self, **kwargs):
        _LAST_CALL.update(kwargs)
        return _FakeGeminiResponse('{"ok": true}')


class _FakeGeminiClient:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.models = _FakeGeminiModels()


_LAST_CALL: dict = {}


@pytest.fixture(autouse=True)
def _clear_last_call():
    _LAST_CALL.clear()
    yield


def test_claude_model_dispatches_to_anthropic(monkeypatch):
    monkeypatch.setattr(llm_module, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(llm_module, "GEMINI_API_KEY", None)

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropicClient)

    result = llm_module.complete_json("system", "user", model="claude-sonnet-5")
    assert result == {"ok": True}
    assert _LAST_CALL["model"] == "claude-sonnet-5"


def test_gemini_model_dispatches_to_gemini(monkeypatch):
    monkeypatch.setattr(llm_module, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(llm_module, "GEMINI_API_KEY", "AIza-test")

    from google import genai

    monkeypatch.setattr(genai, "Client", _FakeGeminiClient)

    result = llm_module.complete_json("system", "user", model="gemini-2.5-flash")
    assert result == {"ok": True}
    assert _LAST_CALL["model"] == "gemini-2.5-flash"
    # JSON-mode request should ask Gemini for application/json output.
    assert _LAST_CALL["config"].response_mime_type == "application/json"


def test_gemini_text_mode_requests_plain_text(monkeypatch):
    monkeypatch.setattr(llm_module, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(llm_module, "GEMINI_API_KEY", "AIza-test")

    from google import genai

    monkeypatch.setattr(genai, "Client", _FakeGeminiClient)

    llm_module.complete_text("system", "user", model="gemini-2.5-flash")
    assert _LAST_CALL["config"].response_mime_type == "text/plain"


def test_claude_model_raises_without_anthropic_key(monkeypatch):
    monkeypatch.setattr(llm_module, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(llm_module, "GEMINI_API_KEY", "AIza-test")

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm_module.complete_json("system", "user", model="claude-sonnet-5")


def test_gemini_model_raises_without_gemini_key(monkeypatch):
    monkeypatch.setattr(llm_module, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(llm_module, "GEMINI_API_KEY", None)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        llm_module.complete_json("system", "user", model="gemini-2.5-flash")


def test_extract_json_strips_markdown_fence():
    assert llm_module._extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_handles_raw_json():
    assert llm_module._extract_json('{"a": 1}') == {"a": 1}
