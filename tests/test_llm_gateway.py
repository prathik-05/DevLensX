"""P1-D matrix E: provider gateway tests with mocked transports. No real keys."""
import io
import json
import urllib.request

import pytest

from devlensx.llm.provider import (
    LLMProvider,
    AzureOpenAIProvider,
    GroqProvider,
    GeminiProvider,
    OpenAIProvider,
    OpenRouterProvider,
    OllamaProvider,
    OfflineProvider,
    get_llm_provider,
)


class _FakeHTTPResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        if self.status >= 400:
            raise urllib.request.HTTPError("http://x", self.status, "error", {}, None)
        return self

    def __exit__(self, *args):
        return False


def _chat_payload(text, tokens=10):
    return {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": tokens}}


def _install_fake(monkeypatch, payload=None, status=200, exc=None):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        if exc is not None:
            raise exc
        return _FakeHTTPResponse(payload, status=status)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return captured


# --- Azure ---

def test_azure_payload_shape(monkeypatch):
    cap = _install_fake(monkeypatch, _chat_payload("### LOW: note\nDetail."))
    p = AzureOpenAIProvider(endpoint="https://res.openai.azure.com", api_key="k",
                            deployment="gpt-4o", api_version="2024-02-15-preview")
    assert p.generate("hello", system_prompt="SYS", temperature=0.1, max_tokens=100) == "### LOW: note\nDetail."
    assert cap["url"] == ("https://res.openai.azure.com/openai/deployments/gpt-4o"
                          "/chat/completions?api-version=2024-02-15-preview")
    assert cap["headers"]["Api-key"] == "k"
    assert "Authorization" not in cap["headers"]
    assert cap["body"]["temperature"] == 0.1
    assert cap["body"]["max_tokens"] == 100
    assert cap["body"]["messages"][0] == {"role": "system", "content": "SYS"}
    assert p.last_usage == {"total_tokens": 10}


def test_azure_auth_failure_returns_none(monkeypatch):
    _install_fake(monkeypatch, {}, status=401)
    p = AzureOpenAIProvider(endpoint="https://res.openai.azure.com", api_key="bad", deployment="d")
    assert p.generate("hi") is None


def test_azure_missing_config_no_call(monkeypatch):
    called = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
    assert AzureOpenAIProvider(endpoint="", api_key="", deployment="").generate("hi") is None
    assert called == []


def test_azure_configurable_model_and_version(monkeypatch):
    cap = _install_fake(monkeypatch, _chat_payload("ok"))
    p = AzureOpenAIProvider(endpoint="https://r.openai.azure.com", api_key="k",
                            deployment="my-gpt", api_version="2025-01-01-preview", model="custom")
    assert p.model() == "custom"
    assert p.generate("hi") == "ok"
    assert "deployments/my-gpt" in cap["url"] and "2025-01-01-preview" in cap["url"]


# --- Groq (must NOT route to OpenRouter) ---

def test_groq_own_endpoint(monkeypatch):
    cap = _install_fake(monkeypatch, _chat_payload("ok"))
    p = GroqProvider(api_key="gsk_test")
    assert p.generate("hi") == "ok"
    assert cap["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert "openrouter" not in cap["url"]
    assert isinstance(get_llm_provider("groq"), GroqProvider)


def test_groq_configurable_model(monkeypatch):
    cap = _install_fake(monkeypatch, _chat_payload("ok"))
    GroqProvider(api_key="gsk_test", model="llama-test").generate("hi")
    assert cap["body"]["model"] == "llama-test"


# --- Gemini ---

def test_gemini_payload_shape(monkeypatch):
    payload = {"candidates": [{"content": {"parts": [{"text": "gemini says hi"}]}}]}
    cap = _install_fake(monkeypatch, payload)
    p = GeminiProvider(api_key="gkey", model="gemini-2.0-flash")
    assert p.generate("hi", system_prompt="SYS") == "gemini says hi"
    assert "gemini-2.0-flash:generateContent" in cap["url"]
    assert "gkey" in cap["url"]


def test_gemini_malformed_response_returns_none(monkeypatch):
    _install_fake(monkeypatch, {"nope": True})
    assert GeminiProvider(api_key="gkey").generate("hi") is None


# --- OpenAI / OpenRouter ---

def test_openai_endpoint_and_key(monkeypatch):
    cap = _install_fake(monkeypatch, _chat_payload("ok"))
    OpenAIProvider(api_key="sk-test", model="gpt-4o").generate("hi")
    assert cap["url"] == "https://api.openai.com/v1/chat/completions"
    assert cap["headers"]["Authorization"] == "Bearer sk-test"
    assert cap["body"]["model"] == "gpt-4o"


def test_openrouter_headers_and_model(monkeypatch):
    cap = _install_fake(monkeypatch, _chat_payload("ok"))
    OpenRouterProvider(api_key="sk-or-test").generate("hi")
    assert cap["url"] == "https://openrouter.ai/api/v1/chat/completions"
    lowered = {k.lower(): v for k, v in cap["headers"].items()}
    assert lowered.get("x-title") == "DevLensX Platform"


# --- Ollama (no credentials) ---

def test_ollama_no_key_required(monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    cap = _install_fake(monkeypatch, _chat_payload("local ok"))
    p = OllamaProvider()
    assert p.generate("hi") == "local ok"
    assert cap["url"] == "http://localhost:11434/v1/chat/completions"
    assert p.health()["credentials"] == "none"


def test_ollama_unreachable_returns_none(monkeypatch):
    _install_fake(monkeypatch, None, exc=ConnectionError("refused"))
    assert OllamaProvider().generate("hi") is None


# --- Offline ---

def test_offline_never_calls_network(monkeypatch):
    called = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
    p = OfflineProvider()
    assert p.generate("hi") is None
    assert called == []
    assert p.capabilities() == {"llm": False, "streaming": False, "offline": True}
    assert isinstance(get_llm_provider("offline"), OfflineProvider)


# --- Factory ---

def test_factory_azure_and_ollama():
    assert isinstance(get_llm_provider("azure"), AzureOpenAIProvider)
    assert isinstance(get_llm_provider("ollama"), OllamaProvider)
    assert isinstance(get_llm_provider("openai"), OpenAIProvider)
    assert isinstance(get_llm_provider("openrouter"), OpenRouterProvider)
    assert isinstance(get_llm_provider("gemini"), GeminiProvider)


def test_factory_unknown_returns_none_or_legacy():
    import os
    for var in ("AZURE_ENDPOINT", "GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        os.environ.pop(var, None)
    assert get_llm_provider("definitely-not-a-provider") is None


# --- Interface contract ---

def test_all_providers_share_interface():
    instances = [
        AzureOpenAIProvider(endpoint="https://r", api_key="k", deployment="d"),
        GroqProvider(api_key="gsk_x"),
        GeminiProvider(api_key="gkey"),
        OpenAIProvider(api_key="sk-x"),
        OpenRouterProvider(api_key="sk-or-x"),
        OllamaProvider(),
        OfflineProvider(),
    ]
    for inst in instances:
        assert isinstance(inst, LLMProvider)
        assert isinstance(inst.capabilities(), dict)
        assert isinstance(inst.health(), dict)
        assert isinstance(inst.model(), str)
        assert set(inst.capabilities()) >= {"llm", "streaming", "offline"}


@pytest.mark.asyncio
async def test_async_generate_delegates():
    p = OfflineProvider()
    assert await p.agenerate("hi") is None
    chunks = [c async for c in p.astream("hi")]
    assert chunks == []


# --- Engine uses gateway, not provider SDKs ---

def test_engine_constructs_gateway_providers():
    from devlensx.codereview import CodeRabbitEngine, ReviewConfig
    eng = CodeRabbitEngine(ReviewConfig(provider="azure", endpoint="https://r", api_key="k", deployment="d"))
    assert isinstance(eng._gateway_provider(), AzureOpenAIProvider)
    eng2 = CodeRabbitEngine(ReviewConfig(provider="groq", api_key="gsk_x"))
    assert isinstance(eng2._gateway_provider(), GroqProvider)
    eng3 = CodeRabbitEngine(ReviewConfig(provider="ollama"))
    assert isinstance(eng3._gateway_provider(), OllamaProvider)
    eng4 = CodeRabbitEngine(ReviewConfig(provider="offline"))
    assert isinstance(eng4._gateway_provider(), OfflineProvider)


def test_engine_unknown_provider_fails_closed():
    from devlensx.codereview import CodeRabbitEngine, ReviewConfig
    import pytest as _pt
    eng = CodeRabbitEngine(ReviewConfig(provider="wat"))
    with _pt.raises(ValueError):
        eng._gateway_provider()


def test_engine_has_no_provider_sdk_imports():
    import pathlib
    src = pathlib.Path("devlensx/codereview.py").read_text(encoding="utf-8")
    assert "from openai import" not in src
    assert "import openai" not in src
    assert "api.groq.com" not in src
    assert "generativelanguage.googleapis.com" not in src
    assert "openai.azure.com" not in src or "AZURE_ENDPOINT" in src
