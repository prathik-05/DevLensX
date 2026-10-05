import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence.resolver import register_snapshot, get_snapshot_registry
from devlensx.chat.orchestrator import store_model

def test_old_snapshot_preserved_after_incremental():
    client = TestClient(app)
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "inc_repo"
    repo.mkdir()
    (repo / "Foo.java").write_text("public class Foo {}", encoding="utf-8")
    # Initial analyze via direct register + model
    register_snapshot("inc_repo", "run_inc_a", str(repo), "commit_a")
    store_model("run_inc_a", {"repo": "inc_repo", "classes": [{"name": "Foo", "package": "", "stereotype": "Controller", "kind": "class", "file": "Foo.java", "is_test": False, "methods": [], "endpoints": []}]})
    # Incremental with no changes
    resp = client.post("/api/analyze/run_inc_a/incremental", json={"changed_files": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "NO_CHANGES"
    assert data["previous_analysis_run_id"] == "run_inc_a"
    # Old still resolvable
    assert get_snapshot_registry().get("run_inc_a") is not None
    import shutil; shutil.rmtree(tmp, ignore_errors=True)

def test_incremental_creates_new_snapshot():
    client = TestClient(app)
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "inc_repo2"
    repo.mkdir()
    (repo / "Bar.java").write_text("public class Bar {}", encoding="utf-8")
    register_snapshot("inc_repo2", "run_inc_b", str(repo), "commit_b1")
    store_model("run_inc_b", {"repo": "inc_repo2", "classes": [{"name": "Bar", "package": "", "stereotype": "Service", "kind": "class", "file": "Bar.java", "is_test": False, "methods": [], "endpoints": []}]})
    # Add a file to simulate change
    (repo / "Baz.java").write_text("public class Baz {}", encoding="utf-8")
    resp = client.post("/api/analyze/run_inc_b/incremental", json={"changed_files": ["Baz.java"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETE"
    assert data["analysis_run_id"] != "run_inc_b"
    assert get_snapshot_registry().get(data["analysis_run_id"]) is not None
    assert get_snapshot_registry().get("run_inc_b") is not None
    # Old EvidenceRef still blocked against new run (test via evidence security)
    import shutil; shutil.rmtree(tmp, ignore_errors=True)

def test_incremental_rejects_malicious_path():
    client = TestClient(app)
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "inc_repo3"
    repo.mkdir()
    (repo / "X.java").write_text("public class X {}", encoding="utf-8")
    register_snapshot("inc_repo3", "run_inc_c", str(repo), "h1")
    store_model("run_inc_c", {"repo": "inc_repo3", "classes": []})
    resp = client.post("/api/analyze/run_inc_c/incremental", json={"changed_files": ["../evil.java"]})
    assert resp.status_code == 400
    import shutil; shutil.rmtree(tmp, ignore_errors=True)

def test_incremental_rejects_malicious_commit():
    client = TestClient(app)
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "inc_repo4"
    repo.mkdir()
    (repo / "Y.java").write_text("public class Y {}", encoding="utf-8")
    register_snapshot("inc_repo4", "run_inc_d", str(repo), "h1")
    store_model("run_inc_d", {"repo": "inc_repo4", "classes": []})
    resp = client.post("/api/analyze/run_inc_d/incremental", json={"target_commit": "abc; rm -rf /"})
    assert resp.status_code == 400
    import shutil; shutil.rmtree(tmp, ignore_errors=True)
