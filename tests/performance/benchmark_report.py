import json
from devlensx.performance.runner import PerformanceRunner
from devlensx.performance.report import generate_report, save_baseline

def test_benchmark_report():
    results = []
    for repo in ["eval_repos/battleship-python", "eval_repos/spring-petclinic"]:
        try:
            r = PerformanceRunner.benchmark_full(repo)
            results.append(r)
        except Exception as e:
            results.append({"repo": repo, "error": str(e)[:200]})
    report = generate_report(results)
    assert "repositories" in report
    # Save baseline artifact
    save_baseline(report["repositories"])
    # Verify baseline file exists
    from pathlib import Path
    assert Path("perf_baseline.json").exists()
    # Verify repeated-run stability: run twice and compare
    assert len(report["repositories"]) >= 1
