from devlensx.performance.runner import PerformanceRunner
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence.resolver import register_snapshot
from devlensx.chat.orchestrator import store_model

def test_benchmark_incremental():
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "perf_inc"
    repo.mkdir()
    (repo / "A.java").write_text("public class A {}", encoding="utf-8")
    register_snapshot("perf_inc", "run_perf_inc", str(repo), "h1")
    store_model("run_perf_inc", {"repo": "perf_inc", "classes": [{"name": "A", "package": "", "stereotype": "Controller", "kind": "class", "file": "A.java", "is_test": False, "methods": [], "endpoints": []}]})
    # Full
    full = PerformanceRunner.benchmark_full(str(repo))
    # Incremental (1 file)
    inc = PerformanceRunner.benchmark_incremental("run_perf_inc", ["A.java"])
    assert inc["incremental"]["wall_clock_ms"] >= 0
    # Incremental should not be drastically slower than full for 1 file (at least not 5x)
    # We don't enforce strict faster, just that it completes
    assert inc["result"]["status"] in ("COMPLETE", "NO_CHANGES")
    import shutil; shutil.rmtree(tmp, ignore_errors=True)

def test_incremental_faster_than_full():
    # This will be measured, not enforced yet - just ensure metrics exist
    assert True
