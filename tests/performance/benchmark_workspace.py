from devlensx.performance.runner import PerformanceRunner

def test_benchmark_workspace():
    r = PerformanceRunner.benchmark_full("eval_repos/spring-petclinic")
    assert "workspace" in r
    assert r["workspace"]["wall_clock_ms"] < 30000
