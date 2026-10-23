"""
Tests for ScannerManager and RepomixAdapter (P6-B)
"""

import pytest
from devlensx.scanners.manager import ScannerManager
from devlensx.scanners.repomix_adapter import RepomixAdapter
from devlensx.scanners.base import ScannerStatus


def test_scanner_manager_status():
    manager = ScannerManager()
    status = manager.get_status()
    assert "ast-grep" in status
    assert "semgrep" in status
    assert "repomix" in status
    # ast-grep and repomix should be installed on this host
    assert status["ast-grep"]["installed"] is True
    assert status["repomix"]["installed"] is True


def test_repomix_adapter_installed():
    adapter = RepomixAdapter()
    assert adapter.is_installed() is True
    findings = adapter.scan(repo_path=".")
    assert len(findings) == 1
    assert findings[0].status == ScannerStatus.EXECUTED_NO_MATCH


def test_scanner_manager_scan_all():
    manager = ScannerManager()
    # Test scanning a small directory
    findings = manager.scan_all(repo_path="devlensx/scanners")
    assert isinstance(findings, list)
    # Check that candidate findings have explicit statuses
    for f in findings:
        assert isinstance(f.status, ScannerStatus)
        assert f.status in (
            ScannerStatus.EXECUTED_MATCH,
            ScannerStatus.EXECUTED_NO_MATCH,
            ScannerStatus.NOT_INSTALLED,
            ScannerStatus.SKIPPED,
            ScannerStatus.ERROR
        )
