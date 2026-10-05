import re
SECRET_PATTERNS = [
    r"OPENAI_API_KEY\s*=\s*[^\s]+",
    r"GEMINI_API_KEY\s*=\s*[^\s]+",
    r"OPENROUTER_API_KEY\s*=\s*[^\s]+",
    r"Authorization\s*:\s*Bearer\s+[^\s]+",
    r"password\s*=\s*[^\s]+",
    r"secret\s*=\s*[^\s]+",
    r"token\s*=\s*[^\s]+",
    r"sk-[a-zA-Z0-9\-_]+",
    r"Bearer\s+[a-zA-Z0-9\.\-_]+",
]

def redact_secret(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    redacted = text
    for pat in SECRET_PATTERNS:
        redacted = re.sub(pat, "***REDACTED***", redacted, flags=re.IGNORECASE)
    # Also redact .env contents: key=value where value looks like secret
    redacted = re.sub(r"(API_KEY|SECRET|PASSWORD|TOKEN)\s*[=:]\s*[^\s\n]+", r"\1=***REDACTED***", redacted, flags=re.IGNORECASE)
    return redacted

def redact_exception(exc: Exception) -> str:
    # Never leak stack trace with source; just error type and code
    return f"{type(exc).__name__}: ***REDACTED***"

def sanitize_event(event: dict) -> dict:
    sanitized = {}
    for k,v in event.items():
        if isinstance(v, str):
            # Block source-code logging: truncate long strings that look like source
            if len(v) > 500 and ("\n" in v and "class " in v):
                v = "***SOURCE_REDACTED***"
            v = redact_secret(v)
        # Block api_key, secret, token fields
        if "api_key" in k.lower() or "secret" in k.lower() or "authorization" in k.lower():
            v = "***REDACTED***"
        sanitized[k] = v
    return sanitized
