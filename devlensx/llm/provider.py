"""
DevLensX Unified LLM Provider Abstraction Layer (P1-D gateway).

Supports:
  - AzureOpenAIProvider (Azure OpenAI, AZURE_ENDPOINT/KEY/DEPLOYMENT/VERSION)
  - GroqProvider (Groq OpenAI-compatible API)
  - GeminiProvider (Google Gemini API)
  - OpenAIProvider (OpenAI GPT-4o / GPT-4o-mini)
  - OpenRouterProvider (OpenRouter Unified API)
  - OllamaProvider (local Ollama, no credentials)
  - OfflineProvider (zero-credential deterministic fallback marker)

Configuration via Environment Variables:
  - AZURE_ENDPOINT / AZURE_API_KEY / AZURE_DEPLOYMENT / AZURE_API_VERSION
  - GROQ_API_KEY / GROQ_MODEL
  - GEMINI_API_KEY / GEMINI_MODEL
  - OPENAI_API_KEY / OPENAI_MODEL
  - OPENROUTER_API_KEY / OPENROUTER_MODEL
  - OLLAMA_URL / OLLAMA_MODEL

Interface (additive — sync generate() behavior unchanged):
  generate(prompt, system_prompt, temperature, max_tokens)
  agenerate(...)            # async; default runs sync impl in a thread
  astream(...)              # async generator; default yields one chunk
  model() / capabilities() / health()
  last_usage                # token counts from the most recent call, if reported
"""

import asyncio
import os
import urllib.request
import json
from typing import Optional, Dict, Any, List, AsyncGenerator
from dotenv import load_dotenv

load_dotenv()


class LLMProvider:
    """Base interface for all DevLensX LLM providers."""

    def __init__(self) -> None:
        self.last_usage: Optional[Dict[str, Any]] = None
        # P1-G: last transport failure (exception object, in-memory only).
        # Callers classify it via review.telemetry; it is never logged raw.
        self.last_error: Optional[BaseException] = None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        raise NotImplementedError("Subclasses must implement generate()")

    def model(self) -> str:
        return ""

    def capabilities(self) -> Dict[str, Any]:
        return {"llm": True, "streaming": False, "offline": False}

    def health(self) -> Dict[str, Any]:
        return {"ok": False, "reason": "not implemented"}

    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self.generate(prompt, system_prompt, temperature, max_tokens)
        )

    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        # Default: single-chunk stream. Providers with SSE transports
        # override this with true token streaming (P1-E).
        text = await self.agenerate(prompt, system_prompt, temperature, max_tokens)
        if text:
            yield text


# P1-E: bounded incremental SSE reader shared by streaming providers.
_MAX_STREAM_CHARS = 200_000


def _safe_error(exc: BaseException) -> str:
    """P1-F: exception text safe for logs — strips key material that rides
    in URLs (Gemini ?key=), bearer tokens, and secret assignments."""
    try:
        from devlensx.observability.redaction import redact_secret
        text = redact_secret(f"{type(exc).__name__}: {exc}")
    except Exception:
        text = type(exc).__name__
    import re as _re
    text = _re.sub(r"([?&]key=)[^&\s]+", r"\1***REDACTED***", text)
    text = _re.sub(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer ***REDACTED***", text)
    return text[:500]


def _sse_deltas_openai(line: str) -> List[str]:
    """Extract delta.content strings from an OpenAI-compatible SSE data line."""
    text = line.strip()
    if not text.startswith("data:"):
        return []
    payload = text[5:].strip()
    if not payload or payload == "[DONE]":
        return []
    try:
        data = json.loads(payload)
    except Exception:
        return []
    out = []
    for choice in data.get("choices", []) or []:
        delta = (choice.get("delta") or {}).get("content") or ""
        if delta:
            out.append(delta)
    return out


def _sse_deltas_gemini(line: str) -> List[str]:
    """Extract text deltas from a Gemini streamGenerateContent SSE data line."""
    text = line.strip()
    if not text.startswith("data:"):
        return []
    payload = text[5:].strip()
    if not payload:
        return []
    try:
        data = json.loads(payload)
    except Exception:
        return []
    out = []
    for cand in data.get("candidates", []) or []:
        for part in ((cand.get("content") or {}).get("parts", []) or []):
            if part.get("text"):
                out.append(part["text"])
    return out


async def _stream_post(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    timeout: int,
    parse_line: Any,
) -> AsyncGenerator[str, None]:
    """POST with stream:true and yield text deltas incrementally.

    Blocking socket reads run in a worker thread; deltas cross into the
    event loop via a queue. Transport errors propagate to the caller so
    orchestration can fail over deterministically.
    """
    loop = asyncio.get_running_loop()
    queue: "asyncio.Queue[Any]" = asyncio.Queue()
    _DONE = object()

    def _read() -> None:
        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST",
            )
            chars = 0
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for raw in resp:
                    try:
                        line = raw.decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    for delta in parse_line(line):
                        chars += len(delta)
                        if chars > _MAX_STREAM_CHARS:
                            break
                        loop.call_soon_threadsafe(queue.put_nowait, delta)
                    if chars > _MAX_STREAM_CHARS:
                        break
        except Exception as e:  # noqa: BLE001 — caller decides fallback
            loop.call_soon_threadsafe(queue.put_nowait, e)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _DONE)

    await loop.run_in_executor(None, _read)
    while True:
        item = await queue.get()
        if item is _DONE:
            return
        if isinstance(item, Exception):
            raise item
        yield item


class _ChatCompletionsProvider(LLMProvider):
    """Shared OpenAI-compatible chat/completions implementation (urllib, sync)."""

    _name = "chat"

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        timeout: int = 30,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__()
        self.api_key = api_key
        self._model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.extra_headers = extra_headers or {}

    def model(self) -> str:
        return self._model

    def health(self) -> Dict[str, Any]:
        if not self.api_key and self._requires_key():
            return {"ok": False, "reason": "missing credential"}
        return {"ok": True, "model": self._model, "endpoint": self.base_url}

    def _requires_key(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        if self._requires_key() and not self.api_key:
            return None
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: Dict[str, Any] = {"model": self._model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        headers.update(self.extra_headers)
        try:
            req = urllib.request.Request(
                self.base_url + "/chat/completions",
                data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    usage = result.get("usage")
                    if isinstance(usage, dict):
                        self.last_usage = {"total_tokens": usage.get("total_tokens", 0)}
                    return (choices[0].get("message", {}).get("content", "") or "").strip() or None
        except Exception as e:
            self.last_error = e
            print(f"[{self._name} Warning] API call failed: {_safe_error(e)}")
        return None

    def _stream_payload(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
    ) -> tuple:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: Dict[str, Any] = {
            "model": self._model, "messages": messages,
            "temperature": temperature, "stream": True,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        headers = {"Content-Type": "application/json",
                   "Accept": "text/event-stream",
                   "Authorization": f"Bearer {self.api_key}"}
        headers.update(self.extra_headers)
        return payload, headers

    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        if self._requires_key() and not self.api_key:
            return
        payload, headers = self._stream_payload(prompt, system_prompt, temperature, max_tokens)
        async for delta in _stream_post(
            self.base_url + "/chat/completions", headers, payload, self.timeout,
            _sse_deltas_openai,
        ):
            yield delta


class GeminiProvider(LLMProvider):
    _FALLBACK_MODELS = ("gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest", "gemini-1.5-pro")
    _CACHE: Dict[str, str] = {}

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__()
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self._model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def model(self) -> str:
        return self._model

    def health(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"ok": False, "reason": "missing GEMINI_API_KEY"}
        return {"ok": True, "model": self._model}

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        if not self.api_key:
            return None

        cache_key = f"{system_prompt or ''}::{prompt}"
        if cache_key in self._CACHE:
            return self._CACHE[cache_key]

        models_to_try = [self._model] + [m for m in self._FALLBACK_MODELS if m != self._model]
        headers = {"Content-Type": "application/json"}

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Directive: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow system directives."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload: Dict[str, Any] = {"contents": contents,
                                   "generationConfig": {"temperature": temperature}}
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        encoded_data = json.dumps(payload).encode("utf-8")

        for m_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={self.api_key}"
            try:
                req = urllib.request.Request(url, data=encoded_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    candidates = result.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            self._model = m_name  # Remember working model
                            res_text = parts[0].get("text", "").strip() or None
                            if res_text:
                                self._CACHE[cache_key] = res_text
                            return res_text
            except urllib.error.HTTPError as e:
                self.last_error = e
                if e.code in (404, 429, 503):
                    time.sleep(0.5)
                    continue  # Try next model in fallback list
                break
            except Exception as e:
                self.last_error = e
                break
        return None

    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            return
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Directive: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow system directives."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        payload: Dict[str, Any] = {"contents": contents,
                                   "generationConfig": {"temperature": temperature}}
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}"
               f":streamGenerateContent?alt=sse&key={self.api_key}")
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        async for delta in _stream_post(url, headers, payload, 30, _sse_deltas_gemini):
            yield delta


class OpenAIProvider(_ChatCompletionsProvider):
    _name = "OpenAIProvider"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(
            api_key=api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", ""),
            model=model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )


class OpenRouterProvider(_ChatCompletionsProvider):
    _name = "OpenRouterProvider"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(
            api_key=api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", ""),
            model=model or os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001"),
            base_url="https://openrouter.ai/api/v1",
            extra_headers={
                "HTTP-Referer": "https://devlensx.local",
                "X-Title": "DevLensX Platform",
            },
        )


class GroqProvider(_ChatCompletionsProvider):
    _name = "GroqProvider"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(
            api_key=api_key if api_key is not None else os.environ.get("GROQ_API_KEY", ""),
            model=model or os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            base_url="https://api.groq.com/openai/v1",
            timeout=12,
        )


class OllamaProvider(_ChatCompletionsProvider):
    _name = "OllamaProvider"

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, **_: Any):
        super().__init__(
            api_key="ollama",
            model=model or os.environ.get("OLLAMA_MODEL", "llama3"),
            base_url=base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434/v1").rstrip("/").removesuffix("/chat/completions"),
            timeout=60,
        )

    def _requires_key(self) -> bool:
        return False

    def health(self) -> Dict[str, Any]:
        return {"ok": True, "model": self._model, "endpoint": self.base_url, "credentials": "none"}


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI via chat/completions REST (reimplemented concept; no copied code)."""

    _name = "AzureOpenAIProvider"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.endpoint = (endpoint or os.environ.get("AZURE_ENDPOINT", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("AZURE_API_KEY", "")
        self.deployment = deployment or os.environ.get("AZURE_DEPLOYMENT", "")
        self.api_version = api_version or os.environ.get("AZURE_API_VERSION", "2024-02-15-preview")
        self._model = model or self.deployment

    def model(self) -> str:
        return self._model

    def capabilities(self) -> Dict[str, Any]:
        return {"llm": True, "streaming": False, "offline": False, "deployment": self.deployment}

    def health(self) -> Dict[str, Any]:
        if not (self.endpoint and self.api_key and self.deployment):
            return {"ok": False, "reason": "missing AZURE_ENDPOINT/AZURE_API_KEY/AZURE_DEPLOYMENT"}
        return {"ok": True, "model": self._model, "deployment": self.deployment}

    def _url(self) -> str:
        return (f"{self.endpoint}/openai/deployments/{self.deployment}"
                f"/chat/completions?api-version={self.api_version}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        if not (self.endpoint and self.api_key and self.deployment):
            return None
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: Dict[str, Any] = {"messages": messages, "temperature": temperature}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        headers = {"Content-Type": "application/json", "api-key": self.api_key}
        try:
            req = urllib.request.Request(
                self._url(), data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    usage = result.get("usage")
                    if isinstance(usage, dict):
                        self.last_usage = {"total_tokens": usage.get("total_tokens", 0)}
                    return (choices[0].get("message", {}).get("content", "") or "").strip() or None
        except Exception as e:
            self.last_error = e
            print(f"[{self._name} Warning] API call failed: {_safe_error(e)}")
        return None

    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        if not (self.endpoint and self.api_key and self.deployment):
            return
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: Dict[str, Any] = {"messages": messages, "temperature": temperature, "stream": True}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        headers = {"Content-Type": "application/json",
                   "Accept": "text/event-stream", "api-key": self.api_key}
        async for delta in _stream_post(self._url(), headers, payload, 30, _sse_deltas_openai):
            yield delta


class OfflineProvider(LLMProvider):
    """Zero-credential marker: no LLM available. Callers fall back to deterministic paths."""

    def model(self) -> str:
        return "offline"

    def capabilities(self) -> Dict[str, Any]:
        return {"llm": False, "streaming": False, "offline": True}

    def health(self) -> Dict[str, Any]:
        return {"ok": True, "mode": "offline", "reason": "no credentials configured"}

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        return None


def get_llm_provider(provider_name: str = "auto", api_key: Optional[str] = None) -> Optional[LLMProvider]:
    """Factory resolving the active LLM provider. P1-D: groq routes to Groq
    (previously misrouted to OpenRouter); azure/ollama/offline supported."""
    provider_name = (provider_name or "auto").lower().strip()

    if provider_name == "azure":
        return AzureOpenAIProvider(api_key=api_key)
    if provider_name == "groq":
        return GroqProvider(api_key=api_key)
    if provider_name == "gemini":
        return GeminiProvider(api_key=api_key)
    if provider_name == "openai":
        return OpenAIProvider(api_key=api_key)
    if provider_name == "openrouter":
        return OpenRouterProvider(api_key=api_key)
    if provider_name == "ollama":
        return OllamaProvider()
    if provider_name == "offline":
        return OfflineProvider()

    if provider_name == "auto":
        if os.environ.get("AZURE_ENDPOINT") and os.environ.get("AZURE_API_KEY"):
            return AzureOpenAIProvider(api_key=api_key)
        if os.environ.get("GROQ_API_KEY"):
            return GroqProvider(api_key=api_key)
        if os.environ.get("GEMINI_API_KEY"):
            return GeminiProvider(api_key=api_key)
        if os.environ.get("OPENAI_API_KEY"):
            return OpenAIProvider(api_key=api_key)
        if os.environ.get("OPENROUTER_API_KEY"):
            return OpenRouterProvider(api_key=api_key)

    # Legacy fallback: any ambient key wins (preserves pre-P1-D behavior)
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiProvider()
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIProvider()
    if os.environ.get("OPENROUTER_API_KEY"):
        return OpenRouterProvider()

    return None
