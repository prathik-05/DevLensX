import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

def call_external_llm(
    prompt: str,
    system_prompt: str = "You are DevLens X Senior AI Architect.",
    provider: str = "auto",
    api_key: str = "",
    base_url: str = "",
    azure_config: Any = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Executes a real external HTTP API request using available LLM providers in .env:
    1. Gemini (GEMINI_API_KEY)
    2. OpenRouter (OPENROUTER_API_KEY or sk-or- key)
    3. Groq (GROQ_API_KEY or gsk_ key)
    4. OpenAI (OPENAI_API_KEY or sk- key)
    5. Local Ollama (http://localhost:11434)
    """
    load_dotenv(override=True)

    gemini_key = api_key if (api_key and not api_key.startswith("sk-") and not api_key.startswith("gsk_")) else (os.environ.get("GEMINI_API_KEY") or api_key)
    openrouter_key = api_key if api_key.startswith("sk-or-") else (os.environ.get("OPENROUTER_API_KEY") or api_key)
    groq_key = api_key if api_key.startswith("gsk_") else (os.environ.get("GROQ_API_KEY") or api_key)
    openai_key = api_key if (api_key.startswith("sk-") and not api_key.startswith("sk-or-")) else os.environ.get("OPENAI_API_KEY")

    # 1. Google Gemini API (Primary when GEMINI_API_KEY is present)
    if gemini_key:
        try:
            from devlensx.llm.provider import GeminiProvider
            gp = GeminiProvider(api_key=gemini_key)
            out = gp.generate(prompt=prompt, system_prompt=system_prompt)
            if out:
                return {
                    "success": True,
                    "content": out,
                    "provider": f"Gemini Live API ({gp.model()})",
                    "raw": {"model": gp.model()}
                }
        except Exception as e:
            print(f"[Gemini Exception] {e}")

    # 1. OpenRouter API
    if openrouter_key and openrouter_key.startswith("sk-or-"):
        try:
            model = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "DevLensX"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                },
                timeout=30
            )
            if res.status_code == 200:
                data = res.json()
                msg = data["choices"][0]["message"]
                content = msg.get("content") or msg.get("reasoning") or ""
                if not content and "text" in msg:
                    content = msg["text"]
                return {
                    "success": True,
                    "content": content.strip(),
                    "provider": f"OpenRouter Live API ({data.get('model', model)})",
                    "raw": data
                }
            else:
                print(f"[OpenRouter Error] {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[OpenRouter Exception] {e}")

    # 2. Groq API
    if groq_key and groq_key.startswith("gsk_"):
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                },
                timeout=12
            )
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "content": content,
                    "provider": "Groq Live API (llama-3.3-70b-versatile)",
                    "raw": data
                }
            else:
                print(f"[Groq Error] {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[Groq Exception] {e}")

    # 3. OpenAI API
    if openai_key and openai_key.startswith("sk-"):
        try:
            res = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                },
                timeout=12
            )
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "content": content,
                    "provider": "OpenAI Live API (gpt-4o-mini)",
                    "raw": data
                }
            else:
                print(f"[OpenAI Error] {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[OpenAI Exception] {e}")

    # 4. Local Ollama (Free Local LLM)
    ollama_url = base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
    try:
        res = requests.post(
            ollama_url,
            json={
                "model": "llama3",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            },
            timeout=3
        )
        if res.status_code == 200:
            data = res.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "success": True,
                "content": content,
                "provider": "Ollama Local LLM (Live API)",
                "raw": data
            }
    except Exception:
        pass

    return {
        "success": False,
        "error": "No working LLM API Key configured in .env or active providers unreachable.",
        "provider": provider
    }
