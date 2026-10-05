import uuid
import contextvars

_request_id_var = contextvars.ContextVar("request_id", default=None)

def get_request_id():
    val = _request_id_var.get()
    if not val:
        val = f"req-{uuid.uuid4().hex[:8]}"
        _request_id_var.set(val)
    return val

def set_request_id(rid: str):
    _request_id_var.set(rid)
    return rid

def new_request_id():
    rid = f"req-{uuid.uuid4().hex[:8]}"
    _request_id_var.set(rid)
    return rid
