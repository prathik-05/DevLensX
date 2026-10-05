import time, statistics
from devlensx.performance.runner import PerformanceRunner

def _run(repo, runs=3):
    times=[]
    for _ in range(runs):
        r = PerformanceRunner.benchmark_full(repo)
        times.append(r["parse"]["wall_clock_ms"])
    return {"min": min(times), "median": statistics.median(times), "mean": round(statistics.mean(times),2), "max": max(times), "runs": times}

def test_benchmark_parsing():
    for repo in ["eval_repos/battleship-python", "eval_repos/spring-petclinic"]:
        metrics = _run(repo, runs=2)
        assert metrics["mean"] >= 0
        assert metrics["max"] < 60000  # 60s threshold
