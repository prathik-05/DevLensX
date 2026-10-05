import tempfile, shutil
from pathlib import Path
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence.resolver import register_snapshot, get_snapshot_registry
from devlensx.chat.orchestrator import store_model

client = TestClient(app)

def test_incremental_cross_repo_isolation():
    tmp = tempfile.mkdtemp()
    repo_a = Path(tmp) / "repo_a"
    repo_a.mkdir()
    (repo_a / "A.java").write_text("public class A {}", encoding="utf-8")
    repo_b = Path(tmp) / "repo_b"
    repo_b.mkdir()
    (repo_b / "B.py").write_text("class B: pass", encoding="utf-8")
    register_snapshot("repo_a", "run_a_iso", str(repo_a), "h_a")
    register_snapshot("repo_b", "run_b_iso", str(repo_b), "h_b")
    store_model("run_a_iso", {"repo": "repo_a", "classes": [{"name": "A", "package": "", "stereotype": "Controller", "kind": "class", "file": "A.java", "is_test": False, "methods": [], "endpoints": []}]})
    store_model("run_b_iso", {"repo": "repo_b", "classes": [{"name": "B", "package": "", "stereotype": "Service", "kind": "class", "file": "B.py", "is_test": False, "methods": [], "endpoints": []}]})
    # Incremental on repo_a should not leak repo_b symbols
    resp = client.post("/api/analyze/run_a_iso/incremental", json={"changed_files": ["A.java"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["repository_id"] == "repo_a"
    assert "B" not in data["invalidated_artifacts"]["symbols"]
    # B still resolvable
    assert get_snapshot_registry().get("run_b_iso") is not None
    shutil.rmtree(tmp, ignore_errors=True)
