from devlensx.performance.runner import PerformanceRunner

def test_benchmark_indexing():
    for repo in ["eval_repos/battleship-python", "eval_repos/spring-petclinic"]:
        r = PerformanceRunner.benchmark_full(repo)
        # Graph + vector indexing should complete
        assert r["parse"]["files_processed"] >= 0
        assert "graph" in r
        assert r["total"]["wall_clock_ms"] < 180000
