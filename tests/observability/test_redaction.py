from devlensx.observability.redaction import redact_secret, sanitize_event
def test_redaction():
    s = "OPENAI_API_KEY=sk-abc123 secret mypass"
    r = redact_secret(s)
    assert "sk-abc123" not in r
    assert "***REDACTED***" in r
    ev = {"api_key": "sk-secret", "message": "hello OPENAI_API_KEY=sk-123", "source": "class Foo {}"}
    sanitized = sanitize_event(ev)
    assert sanitized["api_key"] == "***REDACTED***"
    assert "sk-123" not in sanitized["message"]

def test_no_source_logging():
    long_source = "class Foo {\n" + "x\n"*600
    ev = {"event": "analysis", "source": long_source}
    sanitized = sanitize_event(ev)
    assert sanitized["source"] == "***SOURCE_REDACTED***"
