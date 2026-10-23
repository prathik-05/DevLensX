"""
Tests for AstGrepScanner (P6-B & Audit Requirements)
"""

import subprocess
import pytest
from devlensx.scanners.astgrep_scanner import AstGrepScanner
from devlensx.scanners.base import ScannerStatus, CandidateFinding


def test_astgrep_scanner_installed_and_version():
    scanner = AstGrepScanner()
    assert scanner.is_installed() is True
    version = scanner.query_actual_version()
    assert version is not None
    assert "0.51" in version or len(version) > 0


def test_astgrep_scanner_missing_binary(monkeypatch):
    scanner = AstGrepScanner()
    monkeypatch.setattr(scanner, "_resolve_binary", lambda: None)
    assert scanner.is_installed() is False
    findings = scanner.scan(repo_path=".")
    assert len(findings) == 1
    assert findings[0].status == ScannerStatus.NOT_INSTALLED
    assert findings[0].check_id == "astgrep.binary.not_installed"


def test_astgrep_scanner_clean_no_matches(monkeypatch):
    scanner = AstGrepScanner()
    class MockProc:
        returncode = 0
        stdout = "[]"
        stderr = ""

    monkeypatch.setattr(scanner, "query_actual_version", lambda: "0.51.0")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
    findings = scanner.scan(repo_path=".")
    assert len(findings) == 1
    assert findings[0].status == ScannerStatus.EXECUTED_NO_MATCH
    assert findings[0].finding_id == "ASTGREP-CLEAN"
    assert findings[0].tool_version == "0.51.0"


def test_astgrep_scanner_matches(monkeypatch):
    scanner = AstGrepScanner()
    mock_payload = [
        {
            "rule_id": "no-hardcoded-credentials",
            "file": "src/Auth.java",
            "message": "Avoid hardcoded secret in production",
            "severity": "ERROR",
            "range": {
                "start": {"line": 42, "column": 5},
                "end": {"line": 42, "column": 30}
            }
        }
    ]
    import json
    class MockProc:
        returncode = 0
        stdout = json.dumps(mock_payload)
        stderr = ""

    monkeypatch.setattr(scanner, "query_actual_version", lambda: "0.51.0")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
    findings = scanner.scan(repo_path="src")
    assert len(findings) == 1
    f = findings[0]
    assert f.status == ScannerStatus.EXECUTED_MATCH
    assert f.check_id == "no-hardcoded-credentials"
    assert f.file == "src/Auth.java"
    assert f.line == 42
    assert f.line_range == "42-42"
    assert f.severity == "ERROR"
    assert f.tool_version == "0.51.0"
    # Invariant: Scanners produce CandidateFinding; status is EXECUTED_MATCH, NEVER VERIFIED!
    assert f.status != "VERIFIED"


def test_astgrep_scanner_version_mismatch(monkeypatch):
    """
    AUDIT TEST:
    Verifies that when installed ast-grep binary version does not match pinned version,
    an explicit ERROR finding with check_id='astgrep.version.mismatch' is emitted.
    """
    scanner = AstGrepScanner(strict_version=True, pinned_version="0.51.0")
    monkeypatch.setattr(scanner, "query_actual_version", lambda: "0.45.2")
    findings = scanner.scan(repo_path=".")
    assert len(findings) == 1
    assert findings[0].status == ScannerStatus.ERROR
    assert findings[0].check_id == "astgrep.version.mismatch"
    assert findings[0].tool_version == "0.45.2"
    assert "0.45.2" in findings[0].message
    assert "0.51.0" in findings[0].message


def test_astgrep_scanner_malformed_output(monkeypatch):
    scanner = AstGrepScanner()
    class MockProc:
        returncode = 0
        stdout = "NOT_VALID_JSON{foo:bar"
        stderr = ""

    monkeypatch.setattr(scanner, "query_actual_version", lambda: "0.51.0")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
    findings = scanner.scan(repo_path=".")
    assert len(findings) == 1
    assert findings[0].status == ScannerStatus.ERROR
    assert findings[0].check_id == "astgrep.malformed.output"


def test_astgrep_scanner_timeout(monkeypatch):
    scanner = AstGrepScanner()
    def mock_timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd=["ast-grep"], timeout=1)

    monkeypatch.setattr(scanner, "query_actual_version", lambda: "0.51.0")
    monkeypatch.setattr(subprocess, "run", mock_timeout)
    findings = scanner.scan(repo_path=".")
    assert len(findings) == 1
    assert findings[0].status == ScannerStatus.ERROR
    assert findings[0].check_id == "astgrep.execution.timeout"


def test_astgrep_scanner_execution_error(monkeypatch):
    scanner = AstGrepScanner()
    class MockProc:
        returncode = 2
        stdout = ""
        stderr = "Fatal error: rule file not found"

    monkeypatch.setattr(scanner, "query_actual_version", lambda: "0.51.0")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockProc())
    findings = scanner.scan(repo_path=".")
    assert len(findings) == 1
    assert findings[0].status == ScannerStatus.ERROR
    assert findings[0].check_id == "astgrep.execution.error"
