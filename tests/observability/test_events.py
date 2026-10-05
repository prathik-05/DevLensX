from devlensx.observability.events import emit_event, get_events, clear_events
from devlensx.observability.models import ObservabilityContext
def test_events():
    clear_events()
    ctx = ObservabilityContext(repository_id="r", analysis_run_id="run1", commit_hash="abc")
    emit_event("analysis_started", context=ctx)
    evs = get_events()
    assert any(e["event"]=="analysis_started" for e in evs)
    assert all("repository_id" not in e or e["repository_id"]!="source code" for e in evs)
