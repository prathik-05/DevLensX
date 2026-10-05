"""
End-to-end integration tests for P3 CodeTurtle Review Intelligence Pipeline.
"""

import pytest
from devlensx.evidence.resolver import register_snapshot
from devlensx.chat.orchestrator import _model_store
from devlensx.review.codeturtle import CodeTurtleReviewEngine


@pytest.fixture
def mock_snapshot_and_model():
    run_id = "test-ocr-p3-run"
    register_snapshot("test-repo", run_id, "eval_repos/test-repo", "c0ffee1")

    model = {
        "classes": [
            {
                "name": "EmployeeService",
                "file": "src/main/EmployeeService.java",
                "line_start": 20,
                "line_end": 50,
                "stereotype": "Service",
            },
            {
                "name": "EmployeeController",
                "file": "src/main/EmployeeController.java",
                "line_start": 10,
                "line_end": 80,
                "stereotype": "Controller",
            },
        ],
        "graph_edges": [
            {"source": "EmployeeController", "target": "EmployeeService"},
        ],
    }
    _model_store[run_id] = model
    yield run_id
    _model_store.pop(run_id, None)


def test_codeturtle_review_snapshot_not_found():
    with pytest.raises(ValueError, match="SNAPSHOT_NOT_FOUND"):
        CodeTurtleReviewEngine.review(
            diff="diff --git a/x b/x\n+1",
            analysis_run_id="non-existent-run",
        )


def test_codeturtle_review_pipeline_end_to_end(mock_snapshot_and_model):
    run_id = mock_snapshot_and_model
    diff = """diff --git a/src/main/EmployeeService.java b/src/main/EmployeeService.java
--- a/src/main/EmployeeService.java
+++ b/src/main/EmployeeService.java
@@ -25,4 +25,7 @@
     public Employee getEmployee(Long id) {
+        String apiKey = "secret_key_123456789_xyz";
+        // TODO: replace with config
         return repository.findById(id).orElse(null);
     }
"""
    result = CodeTurtleReviewEngine.review(
        diff=diff,
        analysis_run_id=run_id,
        provider="none",
    )

    assert result["product"] == "CodeTurtle AI Review"
    assert result["analysis_run_id"] == run_id
    assert "what_changed" in result
    assert "comments" in result
    assert len(result["comments"]) > 0

    # Verify that comments carry Myers diff_snippet and explicit-action flags
    secret_comment = next((c for c in result["comments"] if c["rule_id"] == "HARDCODED_SECRET"), None)
    assert secret_comment is not None
    assert secret_comment["file"] == "src/main/EmployeeService.java"
    assert secret_comment["line_start"] == 26
    assert secret_comment["verdict"] == "VERIFIED"  # In diff + has AST match!
    assert "diff_snippet" in secret_comment
    assert secret_comment["diff_snippet"]["deleted"] == ["String apiKey = \"secret_key_123456789_xyz\";"]
    assert secret_comment["patch_metadata"]["committable"] is True
    assert secret_comment["patch_metadata"]["verified"] is False
    assert secret_comment["patch_metadata"]["requires_user_action"] is True


def test_codeturtle_negative_constraints_suppression(mock_snapshot_and_model):
    run_id = mock_snapshot_and_model
    # Diff introducing a safe local variable that an untuned check might misflag
    diff = """diff --git a/src/main/EmployeeService.java b/src/main/EmployeeService.java
--- a/src/main/EmployeeService.java
+++ b/src/main/EmployeeService.java
@@ -30,3 +30,4 @@
     public void process() {
+        int localCounter = 0;
     }
"""
    result = CodeTurtleReviewEngine.review(
        diff=diff,
        analysis_run_id=run_id,
        provider="none",
    )
    # Ensure stats tracked correctly
    assert "suppressed_count" in result["stats"]
