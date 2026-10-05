from devlensx.observability.events import emit_event, get_events, clear_events
from devlensx.observability.models import ObservabilityContext
def test_chat_metrics():
    clear_events()
    ctx = ObservabilityContext(repository_id="r", analysis_run_id="run1")
    emit_event("chat_started", context=ctx, extra={"mode": "FAST"})
    emit_event("chat_completed", context=ctx, duration_ms=123, status="completed", counts={"tokens": 100})
    evs = get_events()
    assert any(e["event"]=="chat_started" for e in evs)
    assert any(e["event"]=="chat_completed" for e in evs)
    for e in evs:
        assert "OPENAI_API_KEY" not in str(e)
