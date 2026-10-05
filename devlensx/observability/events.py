import time, threading
from typing import List, Dict, Any
from devlensx.observability.models import Event, ObservabilityContext
from devlensx.observability.redaction import sanitize_event
from devlensx.observability.context import get_request_id

_lock = threading.Lock()
_events: List[Dict[str, Any]] = []

def emit_event(event: str, context: ObservabilityContext = None, duration_ms=None, status=None, counts=None, error_code=None, extra: Dict[str, Any]=None):
    ctx = context or ObservabilityContext()
    # ensure request_id
    req_id = get_request_id()
    ev = Event(event=event, timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), context=ctx, duration_ms=duration_ms, status=status, counts=counts, error_code=error_code, request_id=req_id, extra=extra or {})
    d = ev.to_dict()
    d = sanitize_event(d)
    with _lock:
        _events.append(d)
    return d

def get_events():
    with _lock:
        return list(_events)

def clear_events():
    with _lock:
        _events.clear()

def get_events_by_type(event_type: str):
    with _lock:
        return [e for e in _events if e.get("event")==event_type]
