from devlensx.observability.events import emit_event, get_events, clear_events
from devlensx.observability.models import ObservabilityContext
def test_workspace_metrics():
    clear_events()
    ctx = ObservabilityContext(repository_id="r", analysis_run_id="run1")
    emit_event("workspace_created", context=ctx)
    emit_event("impact_requested", context=ctx)
    evs = get_events()
    assert any(e["event"]=="workspace_created" for e in evs)
