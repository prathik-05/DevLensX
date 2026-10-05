import tempfile, shutil
from pathlib import Path
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.chat.orchestrator import store_model

client = TestClient(app)

def _setup_petclinic_like():
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "petclinic_inc"
    repo.mkdir()
    # Minimal petclinic-like files
    (repo / "OwnerController.java").write_text("package org.example; public class OwnerController { public void createOwner() {} }", encoding="utf-8")
    (repo / "OwnerService.java").write_text("package org.example; public class OwnerService {}", encoding="utf-8")
    (repo / "OwnerRepository.java").write_text("package org.example; public interface OwnerRepository {}", encoding="utf-8")
    from devlensx.evidence.resolver import register_snapshot
    register_snapshot("petclinic_inc", "run_inc_pet_a", str(repo), "commit_a1")
    store_model("run_inc_pet_a", {"repo": "petclinic_inc", "classes": [
        {"name": "OwnerController", "package": "org.example", "stereotype": "Controller", "kind": "class", "file": "OwnerController.java", "is_test": False, "methods": [{"name": "createOwner"}], "endpoints": []},
        {"name": "OwnerService", "package": "org.example", "stereotype": "Service", "kind": "class", "file": "OwnerService.java", "is_test": False, "methods": [], "endpoints": []},
        {"name": "OwnerRepository", "package": "org.example", "stereotype": "Repository", "kind": "interface", "file": "OwnerRepository.java", "is_test": False, "methods": [], "endpoints": []},
    ]})
    return tmp, repo

def test_incremental_modify():
    tmp, repo = _setup_petclinic_like()
    resp = client.post("/api/analyze/run_inc_pet_a/incremental", json={"changed_files": ["OwnerController.java"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("COMPLETE", "NO_CHANGES")
    assert any(f["path"] == "OwnerController.java" for f in data["changed_files"])
    assert any(s["symbol_id"] == "OwnerController" for s in data["changed_symbols"])
    assert "OwnerController" in data["invalidated_artifacts"]["symbols"]
    shutil.rmtree(tmp, ignore_errors=True)

def test_incremental_add():
    tmp, repo = _setup_petclinic_like()
    (repo / "OwnerValidator.java").write_text("package org.example; public class OwnerValidator {}", encoding="utf-8")
    resp = client.post("/api/analyze/run_inc_pet_a/incremental", json={"changed_files": ["OwnerValidator.java"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETE"
    # New snapshot should exist
    assert data["analysis_run_id"] != "run_inc_pet_a"
    assert get_snapshot_registry().get(data["analysis_run_id"]) is not None
    shutil.rmtree(tmp, ignore_errors=True)

def test_incremental_delete():
    tmp, repo = _setup_petclinic_like()
    (repo / "OwnerRepository.java").unlink()
    resp = client.post("/api/analyze/run_inc_pet_a/incremental", json={"changed_files": ["OwnerRepository.java"]})
    assert resp.status_code == 200
    data = resp.json()
    assert any(f["path"] == "OwnerRepository.java" for f in data["changed_files"])
    shutil.rmtree(tmp, ignore_errors=True)

def test_incremental_no_changes():
    tmp, repo = _setup_petclinic_like()
    resp = client.post("/api/analyze/run_inc_pet_a/incremental", json={"changed_files": []})
    assert resp.status_code == 200
    assert resp.json()["status"] == "NO_CHANGES"
    shutil.rmtree(tmp, ignore_errors=True)
