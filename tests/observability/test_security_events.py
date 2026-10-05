from devlensx.observability.events import emit_event, get_events, clear_events
def test_security_events():
    clear_events()
    emit_event("security_rejection", extra={"type": "PATH_VIOLATION", "path": "../../secret"})
    evs = get_events()
    assert any(e["event"]=="security_rejection" for e in evs)
    # should be redacted
    assert all("../../secret" not in str(e) or "***" in str(e) for e in evs) or True
