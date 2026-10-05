"""
P3-H Real-Repository and Adversarial Verification for CodeTurtle OCR Pipeline.
Tests on real repository AST models with adversarial, drifting, and negative constraint cases.
"""

import pytest
from devlensx.evidence.resolver import register_snapshot
from devlensx.chat.orchestrator import _model_store
from devlensx.review.codeturtle import CodeTurtleReviewEngine


@pytest.fixture
def real_employee_snapshot():
    run_id = "run-real-employee-ocr"
    register_snapshot("employee-api", run_id, "eval_repos/Employee-Management-REST-API", "emp1234")

    # Real classes matching Employee-Management-REST-API
    model = {
        "classes": [
            {
                "name": "EmployeeController",
                "file": "src/main/java/net/guides/springboot2/springboot2jpacrudexample/controller/EmployeeController.java",
                "line_start": 20,
                "line_end": 75,
                "stereotype": "Controller",
            },
            {
                "name": "EmployeeRepository",
                "file": "src/main/java/net/guides/springboot2/springboot2jpacrudexample/repository/EmployeeRepository.java",
                "line_start": 10,
                "line_end": 30,
                "stereotype": "Repository",
            },
        ],
        "graph_edges": [
            {"source": "EmployeeController", "target": "EmployeeRepository"},
        ],
    }
    _model_store[run_id] = model
    yield run_id
    _model_store.pop(run_id, None)


def test_real_repo_codeturtle_pipeline(real_employee_snapshot):
    run_id = real_employee_snapshot
    controller_file = "src/main/java/net/guides/springboot2/springboot2jpacrudexample/controller/EmployeeController.java"
    repo_file = "src/main/java/net/guides/springboot2/springboot2jpacrudexample/repository/EmployeeRepository.java"

    diff = f"""diff --git a/{controller_file} b/{controller_file}
--- a/{controller_file}
+++ b/{controller_file}
@@ -25,4 +25,8 @@
     public ResponseEntity<Employee> getEmployeeById(Long id) {{
+        String dbToken = "ghp_mockSecretTokenForTest999";
+        // local stack variable:
+        int localLoopCounter = 0;
         return ResponseEntity.ok(employeeRepository.findById(id).get());
     }}
diff --git a/{repo_file} b/{repo_file}
--- a/{repo_file}
+++ b/{repo_file}
@@ -15,3 +15,5 @@
 public interface EmployeeRepository extends JpaRepository<Employee, Long> {{
+    List<Employee> findByDepartment(String dept);
 }}
"""
    result = CodeTurtleReviewEngine.review(
        diff=diff,
        analysis_run_id=run_id,
        provider="none",
    )

    assert result["product"] == "CodeTurtle AI Review"
    assert result["risk_level"] == "CRITICAL"  # Critical due to hardcoded secret finding
    comments = result["comments"]
    assert len(comments) > 0

    # 1. Hardcoded secret is detected, verified against AST & diff, and has line diff
    secret = next((c for c in comments if c["rule_id"] == "HARDCODED_SECRET"), None)
    assert secret is not None
    assert secret["file"] == controller_file
    assert secret["line_start"] == 26
    assert secret["verdict"] == "VERIFIED"
    assert "diff_snippet" in secret
    assert secret["diff_snippet"]["deleted"] == ['String dbToken = "ghp_mockSecretTokenForTest999";']
    assert secret["patch_metadata"]["committable"] is True
    assert secret["patch_metadata"]["requires_user_action"] is True

    # 2. Local variable did not produce a bogus thread-safety false positive
    thread_safety = [c for c in comments if "thread" in c["category"].lower()]
    assert len(thread_safety) == 0


def test_real_repo_cross_file_relocation(real_employee_snapshot):
    run_id = real_employee_snapshot
    controller_file = "src/main/java/net/guides/springboot2/springboot2jpacrudexample/controller/EmployeeController.java"
    repo_file = "src/main/java/net/guides/springboot2/springboot2jpacrudexample/repository/EmployeeRepository.java"

    diff = f"""diff --git a/{controller_file} b/{controller_file}
--- a/{controller_file}
+++ b/{controller_file}
@@ -25,3 +25,4 @@
     public ResponseEntity<Employee> getEmployeeById(Long id) {{
+        // unvalidated endpoint
     }}
diff --git a/{repo_file} b/{repo_file}
--- a/{repo_file}
+++ b/{repo_file}
@@ -15,3 +15,5 @@
 public interface EmployeeRepository extends JpaRepository<Employee, Long> {{
+    List<Employee> findByDepartment(String dept);
 }}
"""
    # Adversarial LLM hallucination: LLM filed comment on controller, but snippet is in repo_file
    from devlensx.review.relocation import relocate_and_resolve_findings
    llm_findings = [
        {
            "file": controller_file,
            "line_start": 1,
            "line_end": 1,
            "existing_code": "List<Employee> findByDepartment(String dept);",
            "title": "Missing pagination in repository query",
            "explanation": "Query may return unbounded list of employees.",
        }
    ]

    relocated = relocate_and_resolve_findings(llm_findings, diff)
    assert len(relocated) == 1
    f = relocated[0]
    # Invariant: uniquely relocated to EmployeeRepository.java with exact line 16!
    assert f["file"] == repo_file
    assert f["relocated_from"] == controller_file
    assert f["line_start"] == 16
    assert f["resolved_by"] == "cross_file_relocation"
