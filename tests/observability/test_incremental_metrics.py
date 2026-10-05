from devlensx.observability.events import emit_event, get_events, clear_events
from devlensx.observability.models import ObservabilityContext
def test_incremental_metrics():
    clear_events()
    ctx = ObservabilityContext(repository_id="r", analysis_run_id="run1")
    emit_event("incremental_started", context=ctx, extra={"files_changed": 2})
    emit_event("incremental_completed", context=ctx, duration_ms=412, counts={"symbols_changed": 5})
    evs = get_events()
    assert any(e["event"]=="incremental_started" for e in evs)
