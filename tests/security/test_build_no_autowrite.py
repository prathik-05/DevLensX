"""
Build No-Auto-Write Tests (D10.2.7)
"""
import tempfile, hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence.resolver import register_snapshot

client = TestClient(app)

def _hash_tree(root: Path):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            try:
                h.update(p.relative_to(root).as_posix().encode())
                h.update(p.read_bytes())
            except: pass
    return h.hexdigest()

def test_build_plan_does_not_modify_files():
    tmpdir = tempfile.mkdtemp()
    repo = Path(tmpdir) / "repo_build"
    repo.mkdir()
    (repo / "OwnerController.java").write_text("public class OwnerController {}", encoding="utf-8")
    (repo / "Service.java").write_text("public class Service {}", encoding="utf-8")
    before = _hash_tree(repo)
    snap = register_snapshot("build_repo", "run_build_test", str(repo), "h_build")
    # Need to seed per-run model for BuildPlanner (P1-C: no global fallback)
    from devlensx.chat.orchestrator import _model_store
    _model_store["run_build_test"] = {"repo": "build_repo", "classes": [{"name": "OwnerController", "stereotype": "Controller", "file": "OwnerController.java"}, {"name": "Service", "stereotype": "Service", "file": "Service.java"}]}
    # Also need snapshot registry already
    resp = client.post("/api/workspace/run_build_test/build/plan", json={"task": "Add pagination", "target_symbol": "OwnerController"})
    assert resp.status_code == 200
    data = resp.json()
    assert "steps" in data
    assert len(data["steps"]) > 0
    after = _hash_tree(repo)
    assert before == after, "Repository files were modified by build plan!"
    # git status unchanged check (repo not git-initialized, just ensure no files created)
    new_files = list(repo.rglob("*.java.bak")) + list(repo.rglob("*.new"))
    assert len(new_files) == 0
    import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

def test_build_plan_steps_are_ai_suggestion():
    tmpdir = tempfile.mkdtemp()
    repo = Path(tmpdir) / "repo_build2"
    repo.mkdir()
    (repo / "A.java").write_text("public class A {}", encoding="utf-8")
    register_snapshot("build_repo2", "run_build_test2", str(repo), "h2")
    from devlensx.chat.orchestrator import _model_store
    _model_store["run_build_test2"] = {"repo": "build_repo2", "classes": [{"name": "A", "stereotype": "Controller", "file": "A.java"}]}
    resp = client.post("/api/workspace/run_build_test2/build/plan", json={"task": "Add feature X", "target_symbol": "A"})
    assert resp.status_code == 200
    for step in resp.json().get("steps", []):
        assert step["status"] == "AI_SUGGESTION"
        assert step["verification_required"] is True
    import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
