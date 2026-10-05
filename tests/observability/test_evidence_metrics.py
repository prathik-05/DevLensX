from devlensx.observability.events import emit_event, get_events, clear_events
def test_evidence_metrics():
    clear_events()
    emit_event("evidence_resolution", extra={"resolved": 10, "stale": 1})
    evs = get_events()
    assert any(e["event"]=="evidence_resolution" for e in evs)
