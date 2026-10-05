import time, threading
from typing import List, Dict, Any
from devlensx.observability.models import Metric, ObservabilityContext, StageMetric
from devlensx.observability.redaction import sanitize_event

_lock = threading.Lock()
_metrics: List[Dict[str, Any]] = []

def record_metric(name: str, value: float, unit: str="ms", context: ObservabilityContext=None, extra: Dict[str, Any]=None):
    ctx = context or ObservabilityContext()
    m = Metric(name=name, value=value, unit=unit, context=ctx, extra=extra or {})
    d = m.to_dict()
    d = sanitize_event(d)
    with _lock:
        _metrics.append(d)
    return d

def record_stage(stage: str, wall_clock_ms: float, cpu_time_ms: float=0, success=True, files=0, symbols=0, relationships=0, context: ObservabilityContext=None):
    ctx = context or ObservabilityContext()
    m = StageMetric(stage=stage, wall_clock_ms=wall_clock_ms, cpu_time_ms=cpu_time_ms, success=success, files_processed=files, symbols_processed=symbols, relationships_processed=relationships, context=ctx)
    d = m.to_dict()
    d = sanitize_event(d)
    with _lock:
        _metrics.append(d)
    return d

def get_metrics():
    with _lock:
        return list(_metrics)

def clear_metrics():
    with _lock:
        _metrics.clear()
