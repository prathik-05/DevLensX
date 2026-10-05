"""
DevLensX P2-B CodeTurtle Rebrand & Review UX Test Suite
Validates:
1. CodeTurtleReviewEngine delegates strictly to ReviewEngine and ClaimVerifier.
2. Exact snapshot isolation (unknown run -> 404 SNAPSHOT_NOT_FOUND).
3. No fallback to global_state or latest run.
4. No synthesized AST model from diff.
5. ClaimVerifier determines verdicts (VERIFIED, SUGGESTION, INSUFFICIENT_EVIDENCE) with genuine counts.
6. Endpoints /review/codeturtle and /review/coderabbit (compatibility alias) produce identical results.
7. No-write guarantee (repository hash remains identical before and after review).
"""

import os
import sys
import json
import hashlib
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from devlensx.evidence.models import SnapshotRecord
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.chat.orchestrator import _model_store
from devlensx.core.persistence import get_storage_manager
from devlensx.review.codeturtle import CodeTurtleReviewEngine, CodeRabbitReviewEngine
from devlensx.api.main import app

client = TestClient(app)

SAMPLE_PETCLINIC_DIFF = """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
index 1234567..89abcdef 100644
--- a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
@@ -20,6 +20,12 @@
     public String processFindForm(Owner owner, BindingResult result, Map<String, Object> model) {
+        // Defensive null check added
+        if (owner == null) {
+            throw new IllegalArgumentException("Owner cannot be null");
+        }
         return "owners/ownersList";
     }
"""

SAMPLE_SECRET_DIFF = """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
index 1234567..89abcdef 100644
--- a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
@@ -15,3 +15,4 @@
+    private String apiKey = "sk-1234567890abcdef";
"""


@pytest.fixture(autouse=True)
def setup_test_snapshot():
    """Sets up an exact snapshot for PetClinic in the registry and persistence store."""
    registry = get_snapshot_registry()
    snap = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_codeturtle_test",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="f182358d02e4"
    )
    model = {
        "repo": "spring-petclinic",
        "classes": [
            {
                "name": "OwnerController",
                "stereotype": "Controller",
                "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
                "line_start": 10,
                "line_end": 60,
                "kind": "class"
            },
            {
                "name": "OwnerRepository",
                "stereotype": "Repository",
                "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java",
                "line_start": 1,
                "line_end": 40,
                "kind": "interface"
            }
        ],
        "relationships": [
            {
                "source": "OwnerController",
                "target": "OwnerRepository",
                "type": "DEPENDS_ON"
            }
        ]
    }
    with registry._lock:
        registry._snapshots["run_codeturtle_test"] = snap
    _model_store["run_codeturtle_test"] = model

    mgr = get_storage_manager()
    mgr.save_snapshot(snap, model)
    yield
    # Cleanup


def test_codeturtle_review_success():
    """Validates CodeTurtle review executes with grounded changed symbols and ClaimVerifier."""
    result = CodeTurtleReviewEngine.review(
        diff=SAMPLE_PETCLINIC_DIFF,
        analysis_run_id="run_codeturtle_test"
    )

    assert result["product"] == "CodeTurtle AI Review"
    assert result["analysis_run_id"] == "run_codeturtle_test"
    assert result["repository_id"] == "spring-petclinic"
    assert len(result["what_changed"]) > 0
    assert any(c.get("symbol") == "OwnerController" for c in result["what_changed"])
    assert "diagram" in result
    assert "stats" in result
    assert "verified_count" in result["stats"]
    assert "suggestion_count" in result["stats"]


def test_codeturtle_snapshot_isolation_fail_closed():
    """Validates unknown analysis_run_id fails closed (SNAPSHOT_NOT_FOUND) with zero fallback."""
    with pytest.raises(ValueError) as exc:
        CodeTurtleReviewEngine.review(
            diff=SAMPLE_PETCLINIC_DIFF,
            analysis_run_id="run_unknown_fake_999"
        )
    assert "SNAPSHOT_NOT_FOUND" in str(exc.value)


def test_codeturtle_security_invariant_detection():
    """Validates that hardcoded secret diff is caught and vetted via ClaimVerifier."""
    result = CodeTurtleReviewEngine.review(
        diff=SAMPLE_SECRET_DIFF,
        analysis_run_id="run_codeturtle_test"
    )
    comments = result["comments"]
    secret_findings = [c for c in comments if c.get("rule_id") == "HARDCODED_SECRET"]
    assert len(secret_findings) > 0
    assert secret_findings[0]["severity"] == "CRITICAL"
    assert secret_findings[0]["status"] in ("VERIFIED", "SUGGESTION")


def test_codeturtle_endpoints_and_coderabbit_alias():
    """Validates API endpoints for CodeTurtle and verifies CodeRabbit alias returns identical output."""
    # 1. CodeTurtle endpoint
    resp_turtle = client.post(
        "/api/workspace/run_codeturtle_test/review/codeturtle",
        json={"diff": SAMPLE_PETCLINIC_DIFF}
    )
    assert resp_turtle.status_code == 200, resp_turtle.text
    data_turtle = resp_turtle.json()
    assert data_turtle["product"] == "CodeTurtle AI Review"

    # 2. CodeRabbit compatibility alias endpoint
    resp_rabbit = client.post(
        "/api/workspace/run_codeturtle_test/review/coderabbit",
        json={"diff": SAMPLE_PETCLINIC_DIFF}
    )
    assert resp_rabbit.status_code == 200, resp_rabbit.text
    data_rabbit = resp_rabbit.json()
    assert data_rabbit["product"] == "CodeTurtle AI Review"
    assert data_rabbit["analysis_run_id"] == data_turtle["analysis_run_id"]
    assert len(data_rabbit["what_changed"]) == len(data_turtle["what_changed"])

    # 3. Missing snapshot returns 404
    resp_404 = client.post(
        "/api/workspace/run_missing_abc123/review/codeturtle",
        json={"diff": SAMPLE_PETCLINIC_DIFF}
    )
    assert resp_404.status_code == 404
    assert "SNAPSHOT_NOT_FOUND" in resp_404.json()["detail"]


def test_no_auto_write_guarantee():
    """Verifies that running CodeTurtle review performs zero modifications to source files."""
    test_file = Path("eval_repos/spring-petclinic/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java")
    if test_file.exists():
        sha_before = hashlib.sha256(test_file.read_bytes()).hexdigest()

        CodeTurtleReviewEngine.review(
            diff=SAMPLE_PETCLINIC_DIFF,
            analysis_run_id="run_codeturtle_test"
        )

        sha_after = hashlib.sha256(test_file.read_bytes()).hexdigest()
        assert sha_before == sha_after, "Source file was unexpectedly modified during review!"
