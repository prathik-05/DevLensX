"""Code Rabbit review endpoint tests — mock mode (no LLM provider needed)."""
from fastapi.testclient import TestClient


def _client():
    from devlensx.api.main import app
    return TestClient(app)


def test_codereview_health():
    c = _client()
    r = c.get("/codereview/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "configured" in body
    assert "provider" in body


def test_codereview_review_requires_diff():
    c = _client()
    r = c.post("/codereview/review", json={"diff": ""})
    assert r.status_code == 400


def test_codereview_review_mock_mode():
    c = _client()
    diff = "diff --git a/a.py b/a.py\n+def foo(x):\n+    return x\n-def bar():\n-    pass\n"
    r = c.post("/codereview/review", json={"diff": diff})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]
    assert isinstance(body["findings"], list) and len(body["findings"]) > 0
    assert body["metadata"]["mock"] is True
    assert body["metadata"]["warning"]


def test_codereview_openapi_compat_shape():
    # Code Turtle /review parity: endpoint accepts diff (+ optional context).
    # P0-A: a client-supplied prompt is rejected (system prompt is server-controlled).
    c = _client()
    r = c.post("/codereview/review", json={"diff": "diff --git a/x b/x\n+1"})
    assert r.status_code == 200
    r = c.post("/codereview/review", json={"diff": "diff --git a/x b/x\n+1", "prompt": "Focus on security."})
    assert r.status_code == 422


def test_codereview_repo_aware_mock():
    # Repo-aware mock: real symbols from context, no hardcoded paths
    c = _client()
    ctx = {
        "repo": "demo",
        "classes": [
            {"name": "OwnerController", "stereotype": "Controller", "file": "owner/OwnerController.java",
             "line_start": 1, "line_end": 100, "annotations": ["Controller"]},
            {"name": "OwnerRepository", "stereotype": "Repository", "file": "owner/OwnerRepository.java",
             "line_start": 1, "line_end": 40, "annotations": ["Repository"]},
            {"name": "Owner", "stereotype": "Entity", "file": "owner/Owner.java",
             "line_start": 1, "line_end": 120, "annotations": ["Entity"]},
        ],
        "relationships": [],
        "endpoints": [
            {"route": "/owners", "method": "POST", "handler": "java_OwnerController_create_1"},
            {"route": "/owners", "method": "GET", "handler": "java_OwnerController_index_2"},
        ],
    }
    r = c.post("/codereview/review", json={"diff": "diff --git a/x b/x\n+1", "context": ctx})
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"].get("grounded") is True
    titles = " ".join(f.get("title", "") for f in body["findings"])
    # POST /owners takes input -> flagged; plain GET listing -> correctly skipped
    assert "OwnerController" in titles
    assert "Controller.java" not in titles  # no hardcoded fake paths


def test_codereview_diff_summary_and_changed_lines():
    # P1-B: hunk summary in metadata; changed-line stamping on touched symbols
    c = _client()
    ctx = {
        "repo": "demo", "language": "java",
        "classes": [
            {"name": "OwnerController", "stereotype": "Controller", "kind": "class",
             "file": "owner/OwnerController.java", "line_start": 1, "line_end": 100,
             "annotations": ["Controller"], "metadata": {}},
        ],
        "relationships": [],
        "endpoints": [{"route": "/owners", "method": "POST", "handler": "java_OwnerController_create_1"}],
    }
    diff = ("diff --git a/owner/OwnerController.java b/owner/OwnerController.java\n"
            "--- a/owner/OwnerController.java\n+++ b/owner/OwnerController.java\n"
            "@@ -10,3 +10,4 @@\n x\n-y\n+z\n+w\n")
    r = c.post("/codereview/review", json={"diff": diff, "context": ctx})
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["diff"]["files"] == 1
    assert body["metadata"]["diff"]["added_lines"] == 2
    val = next(f for f in body["findings"] if "validation" in f["title"])
    assert val["changed_line_start"] == 11
    assert val["changed_line_end"] == 12
    assert val["change_kind"] == "MODIFIED"  # hunk mixes removal + additions


def test_codereview_review_repo_requires_analysis_run_id():
    # P1-A: analysis_run_id is required — never an implicit "latest".
    c = _client()
    r = c.post("/codereview/review-repo", json={})
    assert r.status_code == 422


def test_codereview_review_repo_unknown_run():
    c = _client()
    r = c.post("/codereview/review-repo", json={"analysis_run_id": "run_nope_unknown"})
    assert r.status_code == 404


def test_codereview_review_repo_grounded():
    # P1-A: snapshot registered + per-run model stored; global_state untouched.
    from devlensx.evidence.resolver import register_snapshot
    from devlensx.chat.orchestrator import _model_store
    run_id = "run_p1a_grounded"
    register_snapshot("demo-repo", run_id, "eval_repos/demo", "abc123")
    _model_store[run_id] = {
        "repo": "demo",
        "classes": [
            {"name": "OwnerController", "stereotype": "Controller", "kind": "class",
             "file": "owner/OwnerController.java",
             "line_start": 1, "line_end": 100, "annotations": ["Controller"], "metadata": {}},
            {"name": "OwnerRepository", "stereotype": "Repository", "kind": "interface",
             "file": "owner/OwnerRepository.java",
             "line_start": 1, "line_end": 40, "annotations": ["Repository"], "metadata": {}},
        ],
        "relationships": [],
        "endpoints": [{"route": "/owners", "method": "POST", "handler": "java_OwnerController_create_1"}],
        "repo_summary": {"language": "Java", "framework": "Spring"},
    }
    try:
        c = _client()
        r = c.post("/codereview/review-repo", json={"analysis_run_id": run_id})
        assert r.status_code == 200
        body = r.json()
        assert body["findings"]
        assert "OwnerController" in body["findings"][0]["title"]
        assert body["metadata"]["repository_id"] == "demo-repo"
        assert body["metadata"]["analysis_run_id"] == run_id
        assert body["metadata"]["commit_hash"] == "abc123"
    finally:
        _model_store.pop(run_id, None)
