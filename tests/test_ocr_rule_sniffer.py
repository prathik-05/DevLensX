"""
Unit tests for RuleSniffer and Review Constraint Pre-Filtering.
"""

from devlensx.review.rules.system_rules import RuleSniffer, evaluate_negative_constraints
from devlensx.review.rules.rule_catalog import RULE_CATALOG


def test_rule_sniffer_extract_paths_from_diff():
    diff = """diff --git a/src/main/EmployeeController.java b/src/main/EmployeeController.java
--- a/src/main/EmployeeController.java
+++ b/src/main/EmployeeController.java
@@ -10,3 +10,4 @@
+import org.springframework.web.bind.annotation.RestController;
diff --git a/scripts/deploy.py b/scripts/deploy.py
--- a/scripts/deploy.py
+++ b/scripts/deploy.py
@@ -1,2 +1,3 @@
+print("deploy")
"""
    paths = RuleSniffer.extract_paths_from_diff(diff)
    assert "src/main/EmployeeController.java" in paths
    assert "scripts/deploy.py" in paths

    rules = RuleSniffer.sniff(diff)
    rule_ids = [r.id for r in rules]
    assert "java" in rule_ids
    assert "python" in rule_ids


def test_rule_sniffer_prompt_rendering():
    diff = "+++ b/src/App.tsx\n+console.log('hi');"
    prompt = RuleSniffer.render_prompt_for_diff(diff)
    assert "TypeScript & JavaScript" in prompt
    assert "DO NOT REPORT" in prompt
    assert "useEffect" in prompt


def test_evaluate_negative_constraints_thread_safety_local_variable():
    finding = {
        "category": "Concurrency",
        "title": "Thread safety hazard: counter increment is non-atomic",
        "explanation": "The local variable counter in method process() is incremented without synchronization.",
    }
    suppressed, reason = evaluate_negative_constraints(finding)
    assert suppressed is True
    assert "method-local variable" in reason


def test_evaluate_negative_constraints_sql_injection_parameterized():
    finding = {
        "category": "Security",
        "title": "SQL injection detected in query",
        "explanation": "Query concatenates user input.",
    }
    code_context = 'PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");'
    suppressed, reason = evaluate_negative_constraints(finding, code_context)
    assert suppressed is True
    assert "parameterized binding" in reason


def test_evaluate_negative_constraints_npe_null_guarded():
    finding = {
        "category": "Correctness",
        "title": "Potential NullPointerException on employee.getName()",
        "explanation": "employee may be null.",
    }
    code_context = 'if (employee != null) { return employee.getName(); }'
    suppressed, reason = evaluate_negative_constraints(finding, code_context)
    assert suppressed is True
    assert "explicit null check" in reason


def test_evaluate_negative_constraints_real_issue_not_suppressed():
    finding = {
        "category": "Security",
        "title": "Hardcoded AWS secret key in production code",
        "explanation": "Line contains raw secret AKIAIOSFODNN7EXAMPLE",
    }
    code_context = 'String secret = "AKIAIOSFODNN7EXAMPLE";'
    suppressed, reason = evaluate_negative_constraints(finding, code_context)
    assert suppressed is False
    assert reason is None
