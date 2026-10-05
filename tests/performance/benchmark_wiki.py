from devlensx.performance.runner import PerformanceRunner

def test_benchmark_wiki():
    r = PerformanceRunner.benchmark_full("eval_repos/spring-petclinic")
    assert "wiki" in r
    assert r["wiki"]["wall_clock_ms"] >= 0
    assert r["wiki"]["wall_clock_ms"] < 60000
