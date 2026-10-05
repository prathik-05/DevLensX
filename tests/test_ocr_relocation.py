"""
Unit tests for Diff Relocation and Cross-File Line Resolver.
"""

from devlensx.review.relocation import (
    parse_diff_files,
    resolve_from_hunks,
    relocate_across_files,
    relocate_and_resolve_findings,
)


SAMPLE_DIFF = """diff --git a/src/main/EmployeeService.java b/src/main/EmployeeService.java
--- a/src/main/EmployeeService.java
+++ b/src/main/EmployeeService.java
@@ -25,4 +25,7 @@
     public Employee getEmployee(Long id) {
+        if (id == null) {
+            throw new IllegalArgumentException("ID cannot be null");
+        }
         return repository.findById(id).orElse(null);
     }
diff --git a/src/main/EmployeeController.java b/src/main/EmployeeController.java
--- a/src/main/EmployeeController.java
+++ b/src/main/EmployeeController.java
@@ -40,3 +40,4 @@
     public ResponseEntity<Employee> findById(@PathVariable Long id) {
+        // unvalidated call
         return ResponseEntity.ok(service.getEmployee(id));
     }
"""


def test_parse_diff_files():
    files = parse_diff_files(SAMPLE_DIFF)
    assert len(files) == 2
    assert files[0].new_path == "src/main/EmployeeService.java"
    assert files[1].new_path == "src/main/EmployeeController.java"
    assert len(files[0].hunks) == 1
    assert files[0].hunks[0].new_start == 25


def test_resolve_from_hunk_accurate_lines():
    files = parse_diff_files(SAMPLE_DIFF)
    service_file = files[0]

    snippet = """if (id == null) {
        throw new IllegalArgumentException("ID cannot be null");
    }"""
    span = resolve_from_hunks(service_file, snippet)
    assert span is not None
    start, end = span
    assert start == 26
    assert end == 28


def test_cross_file_relocation_unique_match():
    # LLM incorrectly filed finding against EmployeeController.java instead of EmployeeService.java
    findings = [
        {
            "file": "src/main/EmployeeController.java",
            "line_start": 1,  # drifting/hallucinated line
            "line_end": 1,
            "existing_code": """if (id == null) {
                throw new IllegalArgumentException("ID cannot be null");
            }""",
            "title": "Validation check in service",
        }
    ]

    relocated = relocate_and_resolve_findings(findings, SAMPLE_DIFF)
    assert len(relocated) == 1
    f = relocated[0]
    assert f["file"] == "src/main/EmployeeService.java"
    assert f["relocated_from"] == "src/main/EmployeeController.java"
    assert f["line_start"] == 26
    assert f["line_end"] == 28
    assert f["resolved_by"] == "cross_file_relocation"


def test_cross_file_relocation_ambiguous_yields_insufficient_evidence():
    # Diff with duplicate code in two separate files
    ambiguous_diff = """diff --git a/a.txt b/a.txt
--- a/a.txt
+++ b/a.txt
@@ -1,2 +1,3 @@
+common_boilerplate();
diff --git a/b.txt b/b.txt
--- a/b.txt
+++ b/b.txt
@@ -1,2 +1,3 @@
+common_boilerplate();
"""
    findings = [
        {
            "file": "c.txt",  # Neither a.txt nor b.txt
            "line_start": 0,
            "line_end": 0,
            "existing_code": "common_boilerplate();",
            "title": "Boilerplate check",
        }
    ]

    res = relocate_and_resolve_findings(findings, ambiguous_diff)
    assert len(res) == 1
    f = res[0]
    # Invariant: Never guess when ambiguous -> INSUFFICIENT_EVIDENCE
    assert f["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert "Ambiguous snippet match" in f["rationale"]
