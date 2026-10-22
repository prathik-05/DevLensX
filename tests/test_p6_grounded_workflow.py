"""
Unit and Integration Tests for P6: Grounded Intelligence Loop & Explainable Engineering Workflow
"""

import pytest
from pathlib import Path
from devlensx.understanding.file_explainer import FileExplainer
from devlensx.scanners import SemgrepScanner, AstGrepScanner, ScannerStatus, CandidateFinding
from devlensx.critic.critic_engine import CriticAgent


class MockGraphStore:
    def query_change_impact(self, class_name):
        if class_name == "OrderService":
            return [{"class_name": "PaymentController"}, {"class_name": "InventoryService"}]
        return []

    def query_blast_radius(self, limit=50):
        return [{"class_name": "OrderService"}]


def test_file_explainer_7_fields_and_3_depths():
    repo_model = {
        "repo": "test_repo",
        "classes": [
            {
                "name": "OrderService",
                "file": "src/main/java/com/app/OrderService.java",
                "kind": "class",
                "stereotype": "Service",
                "package": "com.app",
                "annotations": ["@Service", "@Transactional"],
                "methods": [
                    {"name": "createOrder"},
                    {"name": "cancelOrder"},
                    {"name": "getOrderById"}
                ],
                "fields": [
                    {"name": "orderRepository"},
                    {"name": "paymentClient"}
                ],
                "injected_dependencies": ["OrderRepository", "PaymentClient"],
                "line_start": 20,
                "line_range": "20-150"
            }
        ]
    }

    explainer = FileExplainer(repo_model=repo_model, graph_store=MockGraphStore())

    # 1. Beginner Depth
    res_beg = explainer.explain("src/main/java/com/app/OrderService.java", symbol_name="OrderService", depth="beginner")
    for field in ["in_simple_terms", "purpose", "how_it_works", "code_involved", "dependencies_and_impact", "verification_status", "next_action"]:
        assert field in res_beg, f"Missing field {field} in beginner response"
    assert "kitchen manager" in res_beg["in_simple_terms"].lower() or "receptionist" in res_beg["in_simple_terms"].lower() or "restaurant" in res_beg["in_simple_terms"].lower()
    assert res_beg["verification_status"]["status"] == "VERIFIED"
    assert "Source:" in res_beg["verification_status"]["source_line"]

    # 2. Developer Depth
    res_dev = explainer.explain("src/main/java/com/app/OrderService.java", symbol_name="OrderService", depth="developer")
    for field in ["in_simple_terms", "purpose", "how_it_works", "code_involved", "dependencies_and_impact", "verification_status", "next_action"]:
        assert field in res_dev, f"Missing field {field} in developer response"
    assert "createOrder" in res_dev["how_it_works"]
    assert res_dev["code_involved"]["methods_count"] == 3
    assert res_dev["dependencies_and_impact"]["blast_radius_components_count"] == 2

    # 3. Architect Depth
    res_arch = explainer.explain("src/main/java/com/app/OrderService.java", symbol_name="OrderService", depth="architect")
    for field in ["in_simple_terms", "purpose", "how_it_works", "code_involved", "dependencies_and_impact", "verification_status", "next_action"]:
        assert field in res_arch, f"Missing field {field} in architect response"
    assert "Service component" in res_arch["in_simple_terms"] or "boundary" in res_arch["in_simple_terms"]
    assert "Dependency Injection" in res_arch["how_it_works"]


def test_scanners_not_installed_or_explicit_status(tmp_path):
    # Test on empty isolated temporary path so external tools don't crawl full repo
    semgrep = SemgrepScanner(enabled=True)
    findings = semgrep.scan(repo_path=str(tmp_path))
    assert len(findings) == 1
    assert findings[0].status in (
        ScannerStatus.NOT_INSTALLED,
        ScannerStatus.EXECUTED_MATCH,
        ScannerStatus.EXECUTED_NO_MATCH,
        ScannerStatus.ERROR
    )

    astgrep = AstGrepScanner(enabled=True)
    ag_findings = astgrep.scan(repo_path=str(tmp_path))
    assert len(ag_findings) == 1
    assert ag_findings[0].status in (
        ScannerStatus.NOT_INSTALLED,
        ScannerStatus.EXECUTED_MATCH,
        ScannerStatus.EXECUTED_NO_MATCH,
        ScannerStatus.ERROR
    )


def test_scanner_candidate_to_critic_conversion():
    candidate = CandidateFinding(
        finding_id="TEST-001",
        tool="semgrep",
        check_id="rules.security.sql_injection",
        file="src/db/repo.py",
        line=42,
        message="Potential raw SQL string formatting",
        severity="HIGH",
        status=ScannerStatus.EXECUTED_MATCH,
        repository_id="repo123",
        analysis_run_id="run456",
        commit_hash="abc789"
    )
    critic_finding = candidate.to_critic_finding()
    assert critic_finding["finding_id"] == "TEST-001"
    assert critic_finding["evidence"]["tool"] == "semgrep"
    assert critic_finding["evidence"]["semgrep_confirmed"] is True
    assert critic_finding["snapshot"]["analysis_run_id"] == "run456"


def test_critic_hard_verification_gate_rejects_unsupported_claim():
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "classes": [
            {
                "name": "TokenFilterTest",
                "file": "src/test/java/TokenFilterTest.java",
                "methods": [{"name": "testToken"}],
                "fields": [{"name": "tokenFilter"}]
            }
        ]
    }
    # Claim: Hardcoded secret in a test fixture
    finding = {
        "class_name": "TokenFilterTest",
        "file": "src/test/java/TokenFilterTest.java",
        "category": "Hardcoded Secret",
        "claim": "Class TokenFilterTest contains field 'tokenFilter' which matches secret naming patterns.",
        "evidence": {"field_name": "tokenFilter"}
    }
    result = critic.verify_finding(finding, repo_model)
    # Must fail closed because it's a test fixture / filter reference, NOT VERIFIED
    assert result["verdict"] == "REJECTED"
    assert "test fixture" in result["evidence_trail"]["ast_check"]["details"] or "Fail Closed" in result["evidence_trail"]["ast_check"]["details"]
