from devlensx.performance.runner import PerformanceRunner

def test_benchmark_diagrams():
    r = PerformanceRunner.benchmark_full("eval_repos/spring-petclinic")
    assert "diagrams" in r
    assert r["diagrams"]["wall_clock_ms"] < 30000
