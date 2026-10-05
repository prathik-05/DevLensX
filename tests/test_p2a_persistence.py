"""
DevLensX P2-A Persistence, Integrity, and Exact Snapshot Recovery Test Suite
Validates:
1. Atomic writes, checksum generation and verification.
2. Secret scrubbing and bounded artifact limits.
3. Path traversal rejection.
4. Corruption and tampering detection (fail-closed, no fallback).
5. Exact snapshot recovery across simulated process restarts.
6. Strict cross-run isolation (PetClinic vs Battleship).
7. Codemap 404 SNAPSHOT_NOT_FOUND vs 200 count: 0 distinction.
"""

import os
import sys
import json
import hashlib
import shutil
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from devlensx.evidence.models import SnapshotRecord
from devlensx.core.persistence import (
    SnapshotStorageManager,
    SCHEMA_VERSION,
    MAX_ARTIFACT_SIZE,
    scrub_secrets
)
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.chat.orchestrator import _model_store
from devlensx.codemap import build_codemap_stops, get_codemap_stops, cache_codemap_stops, _codemap_cache
from fastapi.testclient import TestClient
from devlensx.api.main import app


@pytest.fixture
def temp_cache():
    """Isolated temporary cache directory for deterministic test runs."""
    tmp_dir = tempfile.mkdtemp(prefix="devlensx_p2a_test_")
    mgr = SnapshotStorageManager(base_dir=tmp_dir)
    yield mgr, tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_atomic_write_and_manifest(temp_cache):
    mgr, tmp_dir = temp_cache
    snap = SnapshotRecord(
        repository_id="test-repo",
        analysis_run_id="run_atomic_01",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="commit_abc123"
    )
    model = {
        "repo": "test-repo",
        "classes": [{"name": "OwnerController", "file": "OwnerController.java", "line_start": 10, "line_end": 50}],
        "stats": {"classes_count": 1}
    }

    # 1. Save snapshot
    assert mgr.save_snapshot(snap, model) is True

    # 2. Verify files created
    snap_dir = Path(tmp_dir) / "snapshots" / "test-repo" / "run_atomic_01"
    assert (snap_dir / "manifest.json").exists()
    assert (snap_dir / "model.json").exists()

    # 3. Verify manifest contents and checksum
    with open(snap_dir / "manifest.json", "r", encoding="utf-8") as mf:
        manifest = json.load(mf)

    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["repository_id"] == "test-repo"
    assert manifest["analysis_run_id"] == "run_atomic_01"
    assert manifest["commit_hash"] == "commit_abc123"

    with open(snap_dir / "model.json", "rb") as bf:
        expected_sha = hashlib.sha256(bf.read()).hexdigest()
    assert manifest["checksum"] == expected_sha


def test_secret_scrubbing(temp_cache):
    mgr, tmp_dir = temp_cache
    snap = SnapshotRecord(
        repository_id="secret-repo",
        analysis_run_id="run_secret_01",
        repo_path="eval_repos/test",
        commit_hash="c_secret"
    )
    model = {
        "repo": "secret-repo",
        "api_key": "sk-1234567890abcdef",
        "nested": {
            "auth_token": "bearer_xyz",
            "password": "supersecretpassword",
            "safe_field": "public_data"
        },
        "classes": [{"name": "AuthService", "file": "AuthService.java", "line_start": 1, "line_end": 20}]
    }

    assert mgr.save_snapshot(snap, model) is True

    # Load file from disk and assert secrets are scrubbed
    snap_dir = Path(tmp_dir) / "snapshots" / "secret-repo" / "run_secret_01"
    with open(snap_dir / "model.json", "r", encoding="utf-8") as f:
        disk_model = json.load(f)

    assert disk_model["api_key"] == "[SCRUBBED_SECRET]"
    assert disk_model["nested"]["auth_token"] == "[SCRUBBED_SECRET]"
    assert disk_model["nested"]["password"] == "[SCRUBBED_SECRET]"
    assert disk_model["nested"]["safe_field"] == "public_data"


def test_path_traversal_rejection(temp_cache):
    mgr, _ = temp_cache
    bad_snap = SnapshotRecord(
        repository_id="../../etc",
        analysis_run_id="../passwd",
        repo_path="eval_repos/test",
        commit_hash="bad"
    )
    model = {"classes": [{"name": "Malicious"}]}

    assert mgr.save_snapshot(bad_snap, model) is False
    assert mgr.load_snapshot("../passwd") is None


def test_corruption_detection_and_fail_closed(temp_cache):
    mgr, tmp_dir = temp_cache
    snap = SnapshotRecord(
        repository_id="corrupt-repo",
        analysis_run_id="run_corrupt_01",
        repo_path="eval_repos/test",
        commit_hash="c_corrupt"
    )
    model = {
        "repo": "corrupt-repo",
        "classes": [{"name": "CorruptClass", "file": "C.java", "line_start": 1, "line_end": 10}]
    }
    assert mgr.save_snapshot(snap, model) is True

    snap_dir = Path(tmp_dir) / "snapshots" / "corrupt-repo" / "run_corrupt_01"
    model_file = snap_dir / "model.json"
    manifest_file = snap_dir / "manifest.json"

    # Case A: Tampered model content (checksum mismatch)
    with open(model_file, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data["classes"].append({"name": "InjectedClass"})
        f.seek(0)
        json.dump(data, f)
        f.truncate()

    # Must fail closed: return None, no fallback
    assert mgr.load_snapshot("run_corrupt_01") is None

    # Case B: Missing manifest
    manifest_file.unlink()
    assert mgr.load_snapshot("run_corrupt_01") is None

    # Case C: Unsupported schema version
    # Re-save then tamper manifest
    assert mgr.save_snapshot(snap, model) is True
    with open(manifest_file, "r+", encoding="utf-8") as f:
        m = json.load(f)
        m["schema_version"] = "99.0"
        f.seek(0)
        json.dump(m, f)
        f.truncate()

    assert mgr.load_snapshot("run_corrupt_01") is None


def test_exact_recovery_and_isolation_across_restarts():
    """Simulates process restart: clear in-memory registries, then recover run_A and run_B strictly."""
    registry = get_snapshot_registry()

    # 1. Register and persist run_A (PetClinic)
    snap_a = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_petclinic_p2a",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="hash_petclinic"
    )
    model_a = {
        "repo": "spring-petclinic",
        "classes": [
            {"name": "OwnerController", "stereotype": "Controller", "file": "OwnerController.java", "line_start": 1, "line_end": 50},
            {"name": "OwnerRepository", "stereotype": "Repository", "file": "OwnerRepository.java", "line_start": 1, "line_end": 30}
        ]
    }
    from devlensx.core.persistence import get_storage_manager
    mgr = get_storage_manager()
    assert mgr.save_snapshot(snap_a, model_a) is True

    # 2. Register and persist run_B (Battleship)
    snap_b = SnapshotRecord(
        repository_id="battleship-python",
        analysis_run_id="run_battleship_p2a",
        repo_path="eval_repos/battleship-python",
        commit_hash="hash_battleship"
    )
    model_b = {
        "repo": "battleship-python",
        "classes": [
            {"name": "Ship", "stereotype": "Model", "file": "ship.py", "line_start": 1, "line_end": 40},
            {"name": "Board", "stereotype": "Engine", "file": "board.py", "line_start": 1, "line_end": 80}
        ]
    }
    assert mgr.save_snapshot(snap_b, model_b) is True

    # 3. Simulate process restart: wipe all in-memory dictionaries!
    with registry._lock:
        registry._snapshots.clear()
    _model_store.clear()
    _codemap_cache.clear()

    assert "run_petclinic_p2a" not in registry._snapshots
    assert "run_petclinic_p2a" not in _model_store

    # 4. Request run_A: Must restore exact PetClinic model and stops
    stops_a = get_codemap_stops("run_petclinic_p2a")
    assert stops_a is not None
    assert len(stops_a) > 0
    class_names_a = {s["class_name"] for s in stops_a}
    assert "OwnerController" in class_names_a
    assert "Ship" not in class_names_a  # No Battleship contamination!

    # 5. Request run_B: Must restore exact Battleship model and stops
    stops_b = get_codemap_stops("run_battleship_p2a")
    assert stops_b is not None
    assert len(stops_b) > 0
    class_names_b = {s["class_name"] for s in stops_b}
    assert "Ship" in class_names_b
    assert "OwnerController" not in class_names_b  # No PetClinic contamination!

    # 6. Test API endpoints
    client = TestClient(app)

    # run_A API
    resp_a = client.get("/api/codemap/run_petclinic_p2a")
    assert resp_a.status_code == 200
    assert any(s["class_name"] == "OwnerController" for s in resp_a.json()["stops"])

    # run_B API
    resp_b = client.get("/api/codemap/run_battleship_p2a")
    assert resp_b.status_code == 200
    assert any(s["class_name"] == "Ship" for s in resp_b.json()["stops"])

    # Invalid run ID: MUST 404 SNAPSHOT_NOT_FOUND (never fallback to latest run!)
    resp_inv = client.get("/api/codemap/run_nonexistent_xyz999")
    assert resp_inv.status_code == 404
    assert "SNAPSHOT_NOT_FOUND" in resp_inv.json()["detail"]


def test_codemap_zero_stops_vs_missing_snapshot():
    """Validates distinction: valid snapshot with 0 stops -> 200 count:0; unknown snapshot -> 404."""
    from devlensx.core.persistence import get_storage_manager
    mgr = get_storage_manager()

    # 1. Valid snapshot but empty repo (0 classes)
    snap_empty = SnapshotRecord(
        repository_id="empty-repo",
        analysis_run_id="run_empty_repo_p2a",
        repo_path="eval_repos/empty",
        commit_hash="hash_empty"
    )
    # Model with classes empty list is not a valid class parse for save_snapshot,
    # but let's test a valid snapshot registered in registry with 0 classes
    registry = get_snapshot_registry()
    registry.register("empty-repo", "run_empty_repo_p2a", "eval_repos/empty", "hash_empty")
    _model_store["run_empty_repo_p2a"] = {"classes": []}

    client = TestClient(app)
    resp = client.get("/api/codemap/run_empty_repo_p2a")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["stops"] == []

    # 2. Unknown snapshot -> 404 SNAPSHOT_NOT_FOUND
    resp_missing = client.get("/api/codemap/run_completely_unknown_123")
    assert resp_missing.status_code == 404
    assert "SNAPSHOT_NOT_FOUND" in resp_missing.json()["detail"]
