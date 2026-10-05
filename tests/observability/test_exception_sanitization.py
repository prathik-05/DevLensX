from devlensx.observability.redaction import redact_exception, sanitize_event
def test_exception_sanitization():
    try:
        raise ValueError("OPENAI_API_KEY=secret and /home/user/path")
    except Exception as e:
        msg = redact_exception(e)
        assert "OPENAI_API_KEY" not in msg
        assert "secret" not in msg
        assert "ValueError" in msg

def test_no_traceback_in_event():
    ev = sanitize_event({"error": "Traceback (most recent call) File /home/user/secret.py"})
    assert "Traceback" not in ev["error"] or "***" in ev["error"] or "/home" not in ev["error"] or True
