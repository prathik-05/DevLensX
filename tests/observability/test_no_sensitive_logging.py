import os
from devlensx.observability.events import emit_event, get_events, clear_events
from devlensx.observability.models import ObservabilityContext
def test_no_sensitive_logging():
    clear_events()
    os.environ["OPENAI_API_KEY"] = "sk-fake-secret-123"
    os.environ["MY_SECRET"] = "supersecret"
    ctx = ObservabilityContext(repository_id="r", analysis_run_id="run1")
    emit_event("analysis_started", context=ctx, extra={"message": f"OPENAI_API_KEY={os.environ['OPENAI_API_KEY']}", "source": "class Foo {}"})
    evs = get_events()
    for e in evs:
        s = str(e)
        assert "sk-fake-secret" not in s
        assert "supersecret" not in s or "***" in s
    del os.environ["OPENAI_API_KEY"]
    del os.environ["MY_SECRET"]
