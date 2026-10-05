from devlensx.observability.metrics import record_metric, get_metrics, clear_metrics, record_stage
from devlensx.observability.models import ObservabilityContext
def test_metrics():
    clear_metrics()
    ctx = ObservabilityContext(repository_id="r", analysis_run_id="run1")
    record_metric("parse_ms", 123, context=ctx)
    record_stage("parse", 100, success=True, context=ctx)
    ms = get_metrics()
    assert len(ms) >= 2
    assert any(m["name"]=="parse_ms" for m in ms)
