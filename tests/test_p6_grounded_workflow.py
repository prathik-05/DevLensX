"""
Unit and Integration Tests for P6: Grounded Intelligence Loop, Claim-Level Evidence Contract,
and Hardened Adversarial Verifier.
"""

import pytest
from pathlib import Path
from devlensx.understanding.file_explainer import FileExplainer
from devlensx.scanners import SemgrepScanner, AstGrepScanner, ScannerStatus, CandidateFinding
from devlensx.critic.critic_engine import CriticAgent


class MockGraphStore:
    def __init__(self, impact_nodes=None):
        self.impact_nodes = impact_nodes or [
            {"class_name": "PaymentController"},
            {"class_name": "InventoryService"},
            {"class_name": "PaymentController"}  # Intentionally duplicate to test deduplication
        ]

    def query_change_impact(self, class_name):
        if class_name == "OrderService":
            return self.impact_nodes
        return []

    def query_blast_radius(self, limit=50):
        return [{"class_name": "OrderService"}]


def test_file_explainer_claim_level_evidence_contract():
    repo_model = {
        "repo": "test_repo",
        "analysis_run_id": "run-test-123",
        "classes": [
            {
                "name": "OrderService",
                "file": "src/main/java/com/app/OrderService.java",
                "kind": "class",
                "stereotype": "Service",
                "package": "com.app",
                "annotations": ["@Service", "@Transactional"],
                "methods": [
                    {"name": "createOrder", "line_range": "30-55"},
                    {"name": "cancelOrder", "line_range": "56-80"},
                    {"name": "getOrderById", "line_range": "81-100"}
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

    # Developer Depth
    res = explainer.explain("src/main/java/com/app/OrderService.java", symbol_name="OrderService", depth="developer")

    # Contract Field 1: in_simple_terms
    assert isinstance(res["in_simple_terms"], str)
    assert "OrderService" in res["in_simple_terms"]

    # Contract Field 2: purpose { text, status }
    assert isinstance(res["purpose"], dict)
    assert "text" in res["purpose"]
    assert res["purpose"]["status"] in ("VERIFIED", "AI_SUGGESTION")

    # Contract Field 3: how_it_works [ { step, text, verification_status, code_involved, evidence_ids } ]
    assert isinstance(res["how_it_works"], list)
    assert len(res["how_it_works"]) >= 3
    for step in res["how_it_works"]:
        assert "step" in step
        assert "text" in step
        assert step["verification_status"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE")
        assert "code_involved" in step
        assert "evidence_ids" in step

    # Contract Field 4: claims [ { text, verification_status, evidence_ids } ]
    assert isinstance(res["claims"], list)
    assert len(res["claims"]) >= 3
    for claim in res["claims"]:
        assert "text" in claim
        assert claim["verification_status"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE")

    # Contract Field 5: dependencies_and_impact { summary, relationships }
    assert isinstance(res["dependencies_and_impact"], dict)
    assert "summary" in res["dependencies_and_impact"]
    assert isinstance(res["dependencies_and_impact"]["relationships"], list)
    for rel in res["dependencies_and_impact"]["relationships"]:
        assert "source" in rel
        assert "target" in rel
        assert "relation" in rel
        assert "source_citation" in rel
        assert rel["verification_status"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE")

    # Contract Field 6: verification_status { overall, verdicts_breakdown, evidence_registry }
    assert isinstance(res["verification_status"], dict)
    assert res["verification_status"]["overall"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE")
    assert "run-test-123" in res["verification_status"]["source_line"]
    assert "#L20-150" in res["verification_status"]["source_line"]
    assert "verdicts_breakdown" in res["verification_status"]
    assert "evidence_registry" in res["verification_status"]

    # Contract Field 7: next_action
    assert isinstance(res["next_action"], str)
    assert len(res["next_action"]) > 10


def test_secret_detection_literal_credential_with_key_suffix():
    """
    CRITICAL AUDIT CASE:
    Ensure fields ending in _KEY (such as AWS_API_KEY) are NOT exempted if they hold
    an actual literal credential. Must be verified and redacted.
    """
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-sec-001",
        "classes": [
            {
                "name": "CloudCredentials",
                "file": "src/main/java/com/app/CloudCredentials.java",
                "line_start": 10,
                "line_range": "10-40",
                "methods": [],
                "fields": [
                    {
                        "name": "AWS_API_KEY",
                        "type": "String",
                        "initializer": "AKIAIOSFODNN7EXAMPLE",
                        "is_final": True
                    }
                ]
            }
        ]
    }

    finding = {
        "class_name": "CloudCredentials",
        "file": "src/main/java/com/app/CloudCredentials.java",
        "category": "Hardcoded Secret",
        "claim": "Class CloudCredentials contains field 'AWS_API_KEY' with hardcoded secret.",
        "evidence": {
            "field_name": "AWS_API_KEY",
            "value": "AKIAIOSFODNN7EXAMPLE"
        }
    }

    result = critic.verify_finding(finding, repo_model)
    # MUST be VERIFIED because an actual AWS key literal is present!
    assert result["verdict"] == "VERIFIED"
    details = result["evidence_trail"]["ast_check"]["details"]
    assert "AKIA..." in details or "[REDACTED]" in details
    # Literal secret MUST be redacted in output, not printed in cleartext
    assert "AKIAIOSFODNN7EXAMPLE" not in details
    assert "#L10-40" in result["source_line"]


def test_secret_detection_parameter_name_constant_is_rejected():
    """
    Tests that a configuration lookup constant (whose value is merely the property name)
    is rejected as a false positive, NOT marked as a leak.
    """
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-sec-002",
        "classes": [
            {
                "name": "Constants",
                "file": "src/main/java/com/app/Constants.java",
                "line_start": 5,
                "line_range": "5-25",
                "methods": [],
                "fields": [
                    {
                        "name": "PASSWORD_KEY",
                        "type": "String",
                        "initializer": "password",
                        "is_final": True
                    }
                ]
            }
        ]
    }

    finding = {
        "class_name": "Constants",
        "file": "src/main/java/com/app/Constants.java",
        "category": "Hardcoded Secret",
        "claim": "Class Constants contains field 'PASSWORD_KEY' which matches secret naming patterns.",
        "evidence": {
            "field_name": "PASSWORD_KEY",
            "value": "password"
        }
    }

    result = critic.verify_finding(finding, repo_model)
    # Must fail closed: it's a property key name, not a leaked secret
    assert result["verdict"] == "REJECTED"
    assert "configuration property key identifier" in result["evidence_trail"]["ast_check"]["details"]


def test_security_annotation_vs_global_configuration():
    """
    AUDIT CASE:
    Distinguish missing annotation (proven) vs asserting endpoint is unprotected (requires global config).
    """
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-sec-003",
        "classes": [
            {
                "name": "PublicApiController",
                "file": "src/main/java/com/app/PublicApiController.java",
                "line_start": 15,
                "line_range": "15-60",
                "annotations": ["@RestController"],
                "methods": [{"name": "getData", "annotations": ["@GetMapping"]}],
                "fields": []
            }
        ]
    }

    # Case A: Claim asserts 'Required authorization annotation not found'
    finding_missing_ann = {
        "class_name": "PublicApiController",
        "file": "src/main/java/com/app/PublicApiController.java",
        "category": "API Security",
        "claim": "Required authorization annotation not found on handler PublicApiController.",
        "evidence": {}
    }
    res_a = critic.verify_finding(finding_missing_ann, repo_model)
    assert res_a["verdict"] == "VERIFIED"
    assert "Required authorization annotation not found" in res_a["evidence_trail"]["ast_check"]["details"]

    # Case B: Claim asserts 'Endpoint is unprotected and publicly accessible'
    finding_unprotected = {
        "class_name": "PublicApiController",
        "file": "src/main/java/com/app/PublicApiController.java",
        "category": "API Security",
        "claim": "Endpoint is unprotected and publicly accessible without authentication.",
        "evidence": {}
    }
    res_b = critic.verify_finding(finding_unprotected, repo_model)
    # MUST NOT be marked VERIFIED because global security configuration has not proven it unprotected!
    assert res_b["verdict"] != "VERIFIED"
    assert "INSUFFICIENT_EVIDENCE" in res_b["evidence_trail"]["ast_check"]["details"]


def test_maintainability_exact_method_count_and_abstention():
    """
    AUDIT CASE:
    Ensure method count checks strictly compare claimed numbers, and abstain if ambiguous.
    """
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-arch-001",
        "classes": [
            {
                "name": "ComplexService",
                "file": "src/main/java/com/app/ComplexService.java",
                "stereotype": "Service",
                "line_start": 10,
                "line_range": "10-200",
                "methods": [{"name": f"method_{i}"} for i in range(25)],
                "fields": []
            }
        ]
    }

    # Case A: Correct exact count claim (25 methods)
    finding_match = {
        "class_name": "ComplexService",
        "file": "src/main/java/com/app/ComplexService.java",
        "category": "Maintainability",
        "claim": "ComplexService contains 25 methods, violating single responsibility principles.",
        "evidence": {}
    }
    res_a = critic.verify_finding(finding_match, repo_model)
    assert res_a["verdict"] == "VERIFIED"

    # Case B: Exaggerated count claim (40 methods, but class only has 25)
    finding_exaggerated = {
        "class_name": "ComplexService",
        "file": "src/main/java/com/app/ComplexService.java",
        "category": "Maintainability",
        "claim": "ComplexService contains 40 methods, violating single responsibility principles.",
        "evidence": {}
    }
    res_b = critic.verify_finding(finding_exaggerated, repo_model)
    assert res_b["verdict"] == "REJECTED"
    assert "AST Check Failed" in res_b["evidence_trail"]["ast_check"]["details"]

    # Case C: Ambiguous claim with no numerical count -> Abstains with INSUFFICIENT_EVIDENCE
    finding_ambiguous = {
        "class_name": "ComplexService",
        "file": "src/main/java/com/app/ComplexService.java",
        "category": "Maintainability",
        "claim": "ComplexService has too many methods and is a God Class.",
        "evidence": {}
    }
    res_c = critic.verify_finding(finding_ambiguous, repo_model)
    assert res_c["verdict"] == "REJECTED"
    assert "INSUFFICIENT_EVIDENCE" in res_c["evidence_trail"]["ast_check"]["details"]


def test_blast_radius_deduplication_and_abstention():
    """
    AUDIT CASE:
    Ensure dependent nodes from graph queries are deduplicated, and abstain if count is unstated.
    """
    # Graph store returns 3 nodes, but 1 is duplicate -> 2 unique dependents
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-impact-001",
        "classes": [
            {
                "name": "OrderService",
                "file": "src/main/java/com/app/OrderService.java",
                "line_start": 10,
                "line_range": "10-100",
                "methods": [],
                "fields": []
            }
        ]
    }

    # Case A: Claim asserts 2 dependents (exact match after deduplication)
    finding_match = {
        "class_name": "OrderService",
        "file": "src/main/java/com/app/OrderService.java",
        "category": "Change Impact",
        "claim": "Modifying OrderService impacts 2 dependent classes in the codebase.",
        "evidence": {}
    }
    res_a = critic.verify_finding(finding_match, repo_model)
    assert res_a["verdict"] == "VERIFIED"
    assert "Confirmed 2 deduplicated dependents" in res_a["evidence_trail"]["ast_check"]["details"]

    # Case B: Claim asserts 5 dependents -> Fails closed
    finding_too_high = {
        "class_name": "OrderService",
        "file": "src/main/java/com/app/OrderService.java",
        "category": "Change Impact",
        "claim": "Modifying OrderService impacts 5 dependent classes in the codebase.",
        "evidence": {}
    }
    res_b = critic.verify_finding(finding_too_high, repo_model)
    assert res_b["verdict"] == "REJECTED"

    # Case C: Ambiguous claim without count -> Abstains
    finding_no_count = {
        "class_name": "OrderService",
        "file": "src/main/java/com/app/OrderService.java",
        "category": "Change Impact",
        "claim": "Modifying OrderService has high blast radius on other components.",
        "evidence": {}
    }
    res_c = critic.verify_finding(finding_no_count, repo_model)
    assert res_c["verdict"] == "REJECTED"
    assert "INSUFFICIENT_EVIDENCE" in res_c["evidence_trail"]["ast_check"]["details"]
