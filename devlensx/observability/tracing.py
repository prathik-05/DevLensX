import time
from contextlib import contextmanager
from devlensx.observability.events import emit_event
from devlensx.observability.metrics import record_stage
from devlensx.observability.models import ObservabilityContext

@contextmanager
def trace_stage(stage: str, context: ObservabilityContext = None):
    start = time.perf_counter()
    cpu_start = time.process_time()
    try:
        emit_event(f"{stage}_started", context=context, status="started")
        yield
        duration = (time.perf_counter()-start)*1000
        cpu = (time.process_time()-cpu_start)*1000
        emit_event(f"{stage}_completed", context=context, duration_ms=round(duration,2), status="completed")
        record_stage(stage, wall_clock_ms=round(duration,2), cpu_time_ms=round(cpu,2), success=True, context=context)
    except Exception as e:
        duration = (time.perf_counter()-start)*1000
        emit_event(f"{stage}_failed", context=context, duration_ms=round(duration,2), status="failed", error_code=type(e).__name__)
        record_stage(stage, wall_clock_ms=round(duration,2), success=False, context=context)
        raise
