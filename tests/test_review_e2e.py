"""P1-H E2E review journeys on a real repository (battleship-python).

Journey 1: snapshot -> review-repo -> finding -> evidence resolve -> source.
Journey 2: diff stream (offline) -> verified events -> complete.
Journey 3: finding -> ChangePlan (proposals only) -> repo tree unchanged.
Journey 4: wrong snapshot -> controlled error, no review.
"""
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from devlensx.api.main import app
from devlensx.evidence.resolver import register_snapshot
from devlensx.chat.orchestrator import _model_store, store_model
from devlensx.repository_memory import RepositoryIntelligenceEngine

REPO = "eval_repos/battleship-python"
RUN = "run_e2e_battleship"
client = TestClient(app)


def _setup():
    intel = RepositoryIntelligenceEngine().analyze(REPO)
    register_snapshot(intel.model.get("repo", "battleship"), RUN, REPO, "e2e1")
    store_model(RUN, intel.model)
    return intel.model


def _teardown():
    _model_store.pop(RUN, None)


def _hash_tree(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and "__pycache__" not in str(p):
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def test_journey_analyze_review_evidence_source():
    model = _setup()
    try:
        # 1. review the analyzed snapshot
        r = client.post("/codereview/review-repo", json={"analysis_run_id": RUN})
        assert r.status_code == 200
        body = r.json()
        assert body["metadata"]["analysis_run_id"] == RUN
        assert body["findings"], "expected deterministic findings"
        verified = [f for f in body["findings"] if f["verdict"] == "VERIFIED"]
        assert verified, "expected at least one VERIFIED finding"
        assert all(f["evidence_refs"] for f in verified)

        # 2. resolve a VERIFIED ref to real source lines
        ref = verified[0]["evidence_refs"][0]
        ev = client.post("/api/evidence/resolve", json={
            "repository_id": ref["repository_id"],
            "analysis_run_id": ref["analysis_run_id"],
            "file_path": ref["file_path"],
            "line_start": ref["line_start"],
            "line_end": ref["line_end"],
            "commit_hash": ref["commit_hash"],
            "symbol_name": ref["symbol_name"],
        })
        assert ev.status_code == 200
        resolved = ev.json()
        assert resolved["resolved"] is True, resolved
        assert resolved["lines"], "expected source lines for SourceViewer"
    finally:
        _teardown()


def test_journey_diff_stream_offline():
    _setup()
    try:
        diff = ("diff --git a/game.py b/game.py\n--- a/game.py\n+++ b/game.py\n"
                "@@ -10,3 +10,4 @@\n x\n-y\n+z\n+w\n")
        r = client.post("/codereview/review/stream", json={"diff": diff})
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        events = []
        for block in r.text.strip().split("\n\n"):
            lines = dict(ln.split(": ", 1) for ln in block.splitlines() if ": " in ln)
            events.append((lines.get("event"), json.loads(lines.get("data", "{}"))))
        types = [t for t, _ in events]
        assert types[0] == "review_started" and types[-1] == "review_complete"
        findings = [d for t, d in events if t.startswith("finding_")]
        assert findings, "expected finding events from offline stream"
        for d in findings:
            f = d["finding"]
            assert f["verdict"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE", "NOT_VERIFIED")
            if f["verdict"] == "VERIFIED":
                assert f["evidence_refs"]
    finally:
        _teardown()


def test_journey_finding_to_changeplan_no_write():
    _setup()
    try:
        before = _hash_tree(REPO)
        r = client.post("/codereview/review-repo", json={"analysis_run_id": RUN})
        finding = r.json()["findings"][0]
        symbol = (finding.get("evidence_refs") or [{}])[0].get("symbol_name", "")
        plan = client.post(f"/api/workspace/{RUN}/build/plan", json={
            "task": finding["title"], "target_symbol": symbol,
        })
        assert plan.status_code == 200
        steps = plan.json()["steps"]
        assert steps
        assert all(s["status"] == "AI_SUGGESTION" for s in steps)
        assert all(s.get("verification_required") for s in steps)
        assert _hash_tree(REPO) == before, "ChangePlan must never modify files"
        assert "Apply" not in json.dumps(plan.json())
    finally:
        _teardown()


def test_journey_wrong_snapshot_controlled_error():
    _setup()
    try:
        r = client.post("/codereview/review-repo",
                        json={"analysis_run_id": RUN, "repository_id": "other-repo"})
        assert r.status_code == 409
        r = client.post("/codereview/review/stream",
                        json={"diff": "diff --git a/x b/x\n+x", "analysis_run_id": "run_missing"})
        assert r.status_code == 404
    finally:
        _teardown()


def test_journey_provider_unavailable_explicit_offline():
    _setup()
    try:
        r = client.post("/codereview/review-repo", json={"analysis_run_id": RUN})
        body = r.json()
        assert body["metadata"].get("mock") is True
        for f in body["findings"]:
            # no false VERIFIED: every VERIFIED carries refs
            if f["verdict"] == "VERIFIED":
                assert f["evidence_refs"]
    finally:
        _teardown()
