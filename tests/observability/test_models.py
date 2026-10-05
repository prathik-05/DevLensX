from devlensx.observability.models import ObservabilityContext, Metric, Event, HealthStatus, StageMetric
def test_models():
    ctx = ObservabilityContext(repository_id="r", analysis_run_id="run1", commit_hash="abc")
    assert ctx.repository_id == "r"
    m = Metric(name="parse_ms", value=123, context=ctx)
    assert m.name == "parse_ms"
    e = Event(event="analysis_started", timestamp="2024-01-01T00:00:00Z", context=ctx)
    assert e.event == "analysis_started"
    h = HealthStatus()
    assert h.status == "ok"
    s = StageMetric(stage="parse", wall_clock_ms=100, success=True)
    assert s.stage == "parse"
