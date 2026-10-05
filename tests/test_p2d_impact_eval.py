"""
P2-D Targeted Test Suite: Change Impact & Evaluation Lab
Validates:
1. Change Impact exact snapshot recovery across memory wipe.
2. Unknown snapshot fails closed (HTTP 404 / ValueError).
3. Grounded AST & Graph blast radius with affected tests and deterministic Mermaid.
4. Read-Only Planner (NO FILE WRITE invariant — SHA-256 unchanged).
5. Evaluation Lab real dynamic metrics (no hardcoded/fabricated numbers).
"""

import os
import shutil
import tempfile
import hashlib
import pytest
from fastapi.testclient import TestClient

from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.evidence.models import SnapshotRecord
from devlensx.core.persistence import SnapshotStorageManager, get_storage_manager
from devlensx.impact.analyzer import ImpactAnalyzer
from devlensx.impact.models import ImpactResult
from devlensx.build.planner import BuildPlanner
from devlensx.evaluation.runner import GoldenRunner
from devlensx.evaluation.dataset import load_dataset
from devlensx.api.main import app

client = TestClient(app)

SAMPLE_MODEL = {
    "repo": "shop-app",
    "repo_summary": {"language": "java", "framework": "Spring Boot"},
    "classes": [
        {
            "name": "OrderController",
            "stereotype": "Controller",
            "kind": "class",
            "file": "shop/OrderController.java",
            "line_start": 10,
            "line_end": 120,
            "injected_dependencies": ["OrderService"],
            "annotations": ["RestController"],
        },
        {
            "name": "OrderService",
            "stereotype": "Service",
            "kind": "class",
            "file": "shop/OrderService.java",
            "line_start": 15,
            "line_end": 150,
            "injected_dependencies": ["OrderRepository"],
            "annotations": ["Service"],
        },
        {
            "name": "OrderRepository",
            "stereotype": "Repository",
            "kind": "interface",
            "file": "shop/OrderRepository.java",
            "line_start": 5,
            "line_end": 45,
            "injected_dependencies": [],
            "annotations": ["Repository"],
        },
        {
            "name": "OrderServiceTest",
            "stereotype": "Test",
            "kind": "class",
            "file": "shop/OrderServiceTest.java",
            "line_start": 1,
            "line_end": 80,
            "is_test": True,
            "injected_dependencies": ["OrderService"],
        },
    ],
    "relationships": [
        {"source": "OrderController", "target": "OrderService", "type": "DEPENDS_ON"},
        {"source": "OrderService", "target": "OrderRepository", "type": "DEPENDS_ON"},
    ],
    "configurations": ["server.port=8080", "spring.datasource.url=jdbc:h2:mem:test"],
}


@pytest.fixture
def isolated_snapshot(tmp_path):
    storage = SnapshotStorageManager(base_dir=str(tmp_path))
    repo_id = "shop-app"
    run_id = "run_p2d_impact_test"
    commit = "a1b2c3d4e5f6"
    repo_dir = tmp_path / "repo_src"
    repo_dir.mkdir()
    (repo_dir / "shop").mkdir()
    (repo_dir / "shop" / "OrderController.java").write_text("class OrderController {}", encoding="utf-8")
    (repo_dir / "shop" / "OrderService.java").write_text("class OrderService {}", encoding="utf-8")
    (repo_dir / "shop" / "OrderRepository.java").write_text("interface OrderRepository {}", encoding="utf-8")
    (repo_dir / "shop" / "OrderServiceTest.java").write_text("class OrderServiceTest {}", encoding="utf-8")

    snap = SnapshotRecord(
        repository_id=repo_id,
        analysis_run_id=run_id,
        repo_path=str(repo_dir),
        commit_hash=commit,
    )
    saved = storage.save_snapshot(snap, SAMPLE_MODEL)
    assert saved is True

    # Register in global storage manager too
    get_storage_manager().save_snapshot(snap, SAMPLE_MODEL)
    get_snapshot_registry().register(repo_id, run_id, str(repo_dir), commit)

    from devlensx.chat.orchestrator import _model_store
    _model_store[run_id] = SAMPLE_MODEL

    yield {
        "repo_id": repo_id,
        "run_id": run_id,
        "commit": commit,
        "repo_dir": str(repo_dir),
        "storage": storage,
    }


def test_impact_exact_snapshot_recovery_across_memory_wipe(isolated_snapshot):
    """Test 1: Wipe in-memory caches and verify ImpactAnalyzer recovers exact snapshot from disk."""
    run_id = isolated_snapshot["run_id"]

    # In-memory wipe
    from devlensx.chat.orchestrator import _model_store
    _model_store.pop(run_id, None)
    get_snapshot_registry()._snapshots.pop(run_id, None)

    # Perform analysis
    impact = ImpactAnalyzer.analyze("OrderRepository", run_id)
    assert impact.status == "OK"
    assert impact.target_symbol == "OrderRepository"
    assert impact.repository_id == isolated_snapshot["repo_id"]
    assert impact.analysis_run_id == run_id
    assert impact.commit_hash == isolated_snapshot["commit"]

    # Verify direct finding evidence ref has full identity tuple
    assert len(impact.direct) == 1
    ref = impact.direct[0]["evidence_ref"]
    assert ref["repository_id"] == isolated_snapshot["repo_id"]
    assert ref["analysis_run_id"] == run_id
    assert ref["commit_hash"] == isolated_snapshot["commit"]
    assert ref["status"] == "VERIFIED"

    # Verify downstream blast radius contains OrderService and OrderController
    downstream_syms = [d["symbol"] for d in impact.downstream]
    assert "OrderService" in downstream_syms
    assert "OrderController" in downstream_syms

    # Verify associated test is detected
    test_syms = [t["symbol"] for t in impact.tests]
    assert "OrderServiceTest" in test_syms

    # Verify deterministic Mermaid diagram
    assert impact.diagram is not None
    assert "graph TD" in impact.diagram.get("mermaid", "")
    assert "OrderRepository" in impact.diagram.get("mermaid", "")


def test_impact_unknown_snapshot_fails_closed():
    """Test 2: Unknown snapshot fails closed via ValueError and HTTP 404."""
    unknown_run = "run_completely_unknown_9999"

    # Direct python call fails closed
    with pytest.raises(ValueError, match="UNKNOWN_RUN"):
        ImpactAnalyzer.analyze("OrderController", unknown_run)

    # API endpoint fails closed with 404
    resp = client.post(f"/api/workspace/{unknown_run}/impact", json={"target_symbol": "OrderController"})
    assert resp.status_code == 404


def test_target_not_found_clean_isolation(isolated_snapshot):
    """Test 3: Missing target symbol in known snapshot returns TARGET_NOT_FOUND without fabricated paths."""
    run_id = isolated_snapshot["run_id"]
    impact = ImpactAnalyzer.analyze("NonexistentController", run_id)
    assert impact.status == "TARGET_NOT_FOUND"
    assert len(impact.direct) == 0
    assert len(impact.downstream) == 0


def test_build_planner_strictly_read_only(isolated_snapshot):
    """Test 4: BuildPlanner plan creation obeys the NO FILE WRITE invariant."""
    run_id = isolated_snapshot["run_id"]
    repo_dir = isolated_snapshot["repo_dir"]

    # Compute SHA-256 of all files before planner call
    before_hashes = {}
    for root, _, files in os.walk(repo_dir):
        for f in files:
            p = os.path.join(root, f)
            before_hashes[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()

    # Call BuildPlanner
    plan = BuildPlanner.plan("Add audit logging", "OrderService", run_id)
    assert plan.repository_id == isolated_snapshot["repo_id"]
    assert plan.analysis_run_id == run_id
    assert len(plan.steps) >= 1

    # Verify all steps are AI_SUGGESTION
    for step in plan.steps:
        assert step.status == "AI_SUGGESTION"
        assert step.source == "AI_SUGGESTION"

    # Verify verified evidence refs exist
    assert len(plan.evidence_refs) >= 1
    for ref in plan.evidence_refs:
        assert ref.get("status") == "VERIFIED"

    # Compute SHA-256 of all files after planner call
    after_hashes = {}
    for root, _, files in os.walk(repo_dir):
        for f in files:
            p = os.path.join(root, f)
            after_hashes[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()

    # Assert 100% byte-for-byte identity — ZERO files modified, added, or deleted
    assert before_hashes == after_hashes, "CRITICAL: BuildPlanner modified repository files! NO FILE WRITE violated!"


def test_evaluation_lab_dynamic_metrics():
    """Test 5: Evaluation Lab returns dynamically computed metrics from actual runs."""
    cases = GoldenRunner.ensure_dataset()
    assert len(cases) >= 30

    # Run quick 3-case subset
    report = GoldenRunner.run_all(cases[:3])
    assert report["cases"] == 3
    assert report["passed"] + report["failed"] == 3
    assert "verified_claims" in report
    assert "insufficient_claims" in report
    assert "details" in report
    assert len(report["details"]) == 3

    # Verify FastAPI evaluation endpoints
    resp_dataset = client.get("/api/evaluation/dataset")
    assert resp_dataset.status_code == 200
    data = resp_dataset.json()
    assert "cases" in data
    assert len(data["cases"]) >= 30

    resp_report = client.get("/api/evaluation/report")
    assert resp_report.status_code == 200
    rep = resp_report.json()
    assert "cases" in rep or "case_count" in rep or "details" in rep

    # Test POST /api/evaluation/run with limit
    resp_run = client.post("/api/evaluation/run", json={"limit": 2})
    assert resp_run.status_code == 200
    run_res = resp_run.json()
    assert run_res["cases"] is not None
    assert isinstance(run_res["cases"], list)
    assert len(run_res["cases"]) == 2
