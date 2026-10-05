from devlensx.performance.runner import PerformanceRunner

def test_benchmark_chat():
    r = PerformanceRunner.benchmark_full("eval_repos/spring-petclinic")
    assert "chat" in r
    # Chat may have fast/codemap latencies
    assert r["chat"]["wall_clock_ms"] < 30000
