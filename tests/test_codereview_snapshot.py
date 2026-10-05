"""P1-A snapshot-discipline regression tests for review-repo.

Proves the review operates against exactly the requested snapshot:
  PetClinic/run_A -> PetClinic/run_A  OK
  PetClinic/run_A requested as Battleship/run_B  REJECTED
  PetClinic/run_A never falls back to process-global latest
  run_A results unchanged after run_B is analyzed
Findings + metadata retain repository_id / analysis_run_id / commit_hash.
"""
import pytest

from devlensx.evidence.resolver import register_snapshot, get_snapshot_registry
from devlensx.chat.orchestrator import _model_store


def _java_model(repo="petclinic"):
    return {
        "repo": repo,
        "classes": [
            {"name": "OwnerController", "stereotype": "Controller", "kind": "class",
             "file": "owner/OwnerController.java", "line_start": 1, "line_end": 100,
             "annotations": ["Controller"], "metadata": {}},
            {"name": "OwnerRepository", "stereotype": "Repository", "kind": "interface",
             "file": "owner/OwnerRepository.java", "line_start": 1, "line_end": 40,
             "annotations": ["Repository"], "metadata": {}},
        ],
        "relationships": [],
        "endpoints": [{"route": "/owners", "method": "POST", "handler": "java_OwnerController_create_1"}],
        "repo_summary": {"language": "Java", "framework": "Spring"},
    }


def _py_model(repo="battleship"):
    return {
        "repo": repo,
        "classes": [
            {"name": "Game", "stereotype": "Class", "kind": "class", "file": "game.py",
             "line_start": 1, "line_end": 90, "annotations": [], "metadata": {}},
            {"name": "Ship", "stereotype": "Class", "kind": "class", "file": "ship.py",
             "line_start": 1, "line_end": 40, "annotations": [], "metadata": {}},
        ],
        "relationships": [],
        "endpoints": [],
        "repo_summary": {"language": "Python", "framework": ""},
    }


def _client():
    from devlensx.api.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture()
def two_snapshots():
    register_snapshot("petclinic", "run_A", "eval_repos/spring-petclinic", "aaa111")
    _model_store["run_A"] = _java_model("petclinic")
    register_snapshot("battleship", "run_B", "eval_repos/battleship-python", "bbb222")
    _model_store["run_B"] = _py_model("battleship")
    yield ("run_A", "run_B")
    for rid in ("run_A", "run_B"):
        _model_store.pop(rid, None)


def test_run_a_reviews_run_a(two_snapshots):
    run_a, _ = two_snapshots
    r = _client().post("/codereview/review-repo", json={"analysis_run_id": run_a})
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["repository_id"] == "petclinic"
    assert body["metadata"]["analysis_run_id"] == run_a
    assert body["metadata"]["commit_hash"] == "aaa111"
    titles = " ".join(f["title"] for f in body["findings"])
    assert "OwnerController" in titles
    assert "Game" not in titles and "Ship" not in titles
    for f in body["findings"]:
        for ref in f.get("evidence_refs", []):
            assert ref["repository_id"] == "petclinic"
            assert ref["analysis_run_id"] == run_a
            assert ref["commit_hash"] == "aaa111"


def test_run_b_reviews_run_b(two_snapshots):
    _, run_b = two_snapshots
    r = _client().post("/codereview/review-repo", json={"analysis_run_id": run_b})
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["repository_id"] == "battleship"
    titles = " ".join(f["title"] for f in body["findings"])
    assert "OwnerController" not in titles


def test_cross_repository_request_rejected(two_snapshots):
    run_a, _ = two_snapshots
    # run_A belongs to petclinic; requesting it as battleship must fail
    r = _client().post("/codereview/review-repo", json={
        "analysis_run_id": run_a, "repository_id": "battleship",
    })
    assert r.status_code == 409
    assert "MISMATCH" in r.json()["detail"]


def test_commit_mismatch_rejected(two_snapshots):
    run_a, _ = two_snapshots
    r = _client().post("/codereview/review-repo", json={
        "analysis_run_id": run_a, "commit_hash": "deadbeef",
    })
    assert r.status_code == 409
    assert "STALE" in r.json()["detail"]


def test_no_fallback_to_global_latest(two_snapshots):
    """Poison process-global state with repo B; run_A must still review A."""
    from devlensx.api import main as api_main
    run_a, _ = two_snapshots
    api_main.global_state["repo_model"] = _py_model("battleship")
    api_main.global_state["latest_synthesis"] = {"verified_findings": []}
    try:
        r = _client().post("/codereview/review-repo", json={"analysis_run_id": run_a})
        assert r.status_code == 200
        body = r.json()
        titles = " ".join(f["title"] for f in body["findings"])
        assert "OwnerController" in titles
        assert "Game" not in titles
    finally:
        api_main.global_state["repo_model"] = None
        api_main.global_state["latest_synthesis"] = None


def test_snapshot_a_immutable_after_b(two_snapshots):
    run_a, _ = two_snapshots
    c = _client()
    before = c.post("/codereview/review-repo", json={"analysis_run_id": run_a}).json()
    # "Analyze" B afterwards: new snapshot + new model must not touch A
    register_snapshot("battleship", "run_B2", "eval_repos/battleship-python", "ccc333")
    _model_store["run_B2"] = _py_model("battleship")
    try:
        after = c.post("/codereview/review-repo", json={"analysis_run_id": run_a}).json()
    finally:
        _model_store.pop("run_B2", None)
    assert [f["title"] for f in before["findings"]] == [f["title"] for f in after["findings"]]
    assert [f["verdict"] for f in before["findings"]] == [f["verdict"] for f in after["findings"]]


def test_model_evicted_is_controlled_error():
    register_snapshot("lonely", "run_naked", "eval_repos/x", "ddd444")
    _model_store.pop("run_naked", None)
    r = _client().post("/codereview/review-repo", json={"analysis_run_id": "run_naked"})
    assert r.status_code == 404
    assert "MODEL_EVICTED" in r.json()["detail"]


def test_matching_identity_accepted(two_snapshots):
    run_a, _ = two_snapshots
    snap = get_snapshot_registry().get(run_a)
    assert snap is not None and snap.repository_id == "petclinic"
    r = _client().post("/codereview/review-repo", json={
        "analysis_run_id": run_a,
        "repository_id": "petclinic",
        "commit_hash": "aaa111",
    })
    assert r.status_code == 200
