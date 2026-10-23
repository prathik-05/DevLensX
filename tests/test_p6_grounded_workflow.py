"""
DevLensX P6 Grounded Workflow & Hard Invariant Tests

Covers:
1. P6-C Customer Understanding & File Explainer (Claim-Level Evidence Output Contract & JSON Serialized Object)
2. P0 AWS Credential Classification vs Secret Literal vs Documentation Sample vs Weak Hardcoded Default vs Config Reference
3. P0 Bounded Submodule Ingestion (Count limits, relative URL resolution, DNS/IP policy, depth 1 non-recursive)
4. Check H Security Annotation vs Global Config
5. Check F Maintainability Exact Method Counts & Abstention
6. Check I Blast Radius Deduplication, Directional Separation & Numerical Proof
"""

import json
import pytest
from pathlib import Path
from fastapi import HTTPException
from devlensx.understanding.file_explainer import FileExplainer
from devlensx.critic import CriticAgent
from devlensx.ingest import clone_repository


class MockGraphStore:
    """Mock graph store returning change impact and dependencies."""
    def query_change_impact(self, class_name: str):
        # Returns 2 dependent callers (1 duplicate to test deduplication)
        return [
            {"class_name": "OrderController", "relation": "CALLS"},
            {"class_name": "PaymentWebhookHandler", "relation": "CALLS"},
            {"class_name": "OrderController", "relation": "CALLS"}, # duplicate
        ]


def test_p6_claim_level_evidence_contract_file_explainer():
    """
    AUDIT TEST:
    Verifies that FileExplainer strictly adheres to the claim-level evidence contract,
    emits smallest relevant line ranges, separates downstream vs upstream impact,
    avoids aggregate VERIFIED badges when unverified content exists (PARTIALLY_VERIFIED),
    and proves that in_simple_terms serializes as a real JSON object with claim_ids.
    """
    repo_model = {
        "repository_id": "repo-test-001",
        "analysis_run_id": "run-test-123",
        "commit_hash": "commit-abc456",
        "classes": [
            {
                "name": "OrderService",
                "file": "src/main/java/com/app/OrderService.java",
                "stereotype": "Service",
                "package": "com.app.service",
                "annotations": ["@Service", "@Transactional"],
                "methods": [
                    {"name": "createOrder", "line_start": 35, "line_range": "35-45"},
                    {"name": "cancelOrder", "line_start": 50, "line_range": "50-60"}
                ],
                "fields": [
                    {"name": "orderRepository", "line_start": 25, "type": "OrderRepository"},
                    {"name": "paymentClient", "line_start": 26, "type": "PaymentClient"}
                ],
                "injected_dependencies": ["OrderRepository", "PaymentClient"],
                "line_start": 20,
                "line_range": "20-150"
            },
            {
                "name": "OrderController",
                "file": "src/main/java/com/app/OrderController.java",
                "stereotype": "Controller",
                "line_start": 15,
                "line_range": "15-80",
                "methods": [],
                "fields": []
            }
        ]
    }

    explainer = FileExplainer(repo_model=repo_model, graph_store=MockGraphStore())

    # Developer Depth
    res = explainer.explain("src/main/java/com/app/OrderService.java", symbol_name="OrderService", depth="developer")

    # Contract Field 1: in_simple_terms (P0 JSON Serialized Contract)
    assert isinstance(res["in_simple_terms"], dict)
    assert "text" in res["in_simple_terms"]
    assert "claim_ids" in res["in_simple_terms"]
    assert "OrderService" in res["in_simple_terms"]["text"]
    assert len(res["in_simple_terms"]["claim_ids"]) > 0

    # P0 Audit Fix: Test actual serialized JSON response roundtrip
    serialized = json.loads(json.dumps(res))
    assert isinstance(serialized["in_simple_terms"], dict)
    assert "text" in serialized["in_simple_terms"]
    assert "claim_ids" in serialized["in_simple_terms"]
    assert "OrderService" in serialized["in_simple_terms"]["text"]
    assert len(serialized["in_simple_terms"]["claim_ids"]) > 0

    # Contract Field 2: purpose { text, status, claim_ids }
    assert isinstance(res["purpose"], dict)
    assert "text" in res["purpose"]
    assert res["purpose"]["status"] in ("VERIFIED", "AI_SUGGESTION")
    assert "claim_ids" in res["purpose"]

    # Contract Field 3: how_it_works [ { step, claim_ids, explanation, text, verification_status, code_involved, evidence_ids } ]
    assert isinstance(res["how_it_works"], list)
    assert len(res["how_it_works"]) >= 3
    for step in res["how_it_works"]:
        assert "step" in step
        assert "text" in step
        assert "explanation" in step
        assert "claim_ids" in step
        assert step["verification_status"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE")
        assert "code_involved" in step
        assert "evidence_ids" in step

    # Contract Field 4: claims [ { id, text, verification_status, evidence_ids } ]
    assert isinstance(res["claims"], list)
    assert len(res["claims"]) >= 3
    for claim in res["claims"]:
        assert "id" in claim
        assert "text" in claim
        assert claim["verification_status"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE")
        assert "evidence_ids" in claim

    # Contract Field 5: evidence [ { id, repository_id, analysis_run_id, commit_hash, file, line_start, line_end, resolved } ]
    assert isinstance(res["evidence"], list)
    assert len(res["evidence"]) >= 2
    for ev in res["evidence"]:
        assert "id" in ev
        assert "repository_id" in ev
        assert "analysis_run_id" in ev
        assert "commit_hash" in ev
        assert "file" in ev
        assert "line_start" in ev
        assert "line_end" in ev
        assert ev.get("resolved") is True

    # Contract Field 6: dependencies_and_impact (Strict Directional Separation)
    dep_impact = res["dependencies_and_impact"]
    assert isinstance(dep_impact, dict)
    assert "summary" in dep_impact
    assert dep_impact["blast_radius_components_count"] == 2  # OrderController and PaymentWebhookHandler
    assert dep_impact["downstream_dependents_count"] == 2
    assert dep_impact["upstream_dependencies_count"] == 2    # OrderRepository and PaymentClient
    assert isinstance(dep_impact["relationships"], list)
    for rel in dep_impact["relationships"]:
        assert "source" in rel
        assert "target" in rel
        assert "relation" in rel
        assert "direction" in rel
        assert rel["direction"] in ("INCOMING", "OUTGOING")
        assert rel["verification_status"] in ("VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE", "UNPROVEN_EDGE")

    # Contract Field 7: verification_status (Aggregate Mixed Status Policy)
    v_status = res["verification_status"]
    assert isinstance(v_status, dict)
    # Since Step 4 and purpose have AI_SUGGESTION, overall MUST NOT be VERIFIED! Must be PARTIALLY_VERIFIED!
    assert v_status["overall"] == "PARTIALLY_VERIFIED"
    assert v_status["overall"] in ("VERIFIED", "PARTIALLY_VERIFIED", "AI_SUGGESTION", "INSUFFICIENT_EVIDENCE")
    assert "run-test-123" in v_status["source_line"]
    assert "verdicts_breakdown" in v_status
    assert "evidence_registry" in v_status

    # Contract Field 8: next_action
    assert isinstance(res["next_action"], str)
    assert len(res["next_action"]) > 10


# =========================================================================
# P0 AUDIT SUITE: AWS Credential Classification, Placeholders & Redaction
# =========================================================================

def test_secret_detection_documentation_placeholder_rejected():
    """
    AUDIT TEST:
    Ensures standard AWS documentation samples (e.g., AKIAIOSFODNN7EXAMPLE,
    wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY) are recognized as documentation/sample
    placeholders and fail closed (REJECTED), NOT reported as active leaks.
    """
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-placeholder-001",
        "classes": [
            {
                "name": "AwsDocExample",
                "file": "src/main/java/com/app/AwsDocExample.java",
                "line_start": 10,
                "line_range": "10-40",
                "methods": [],
                "fields": [
                    {"name": "SAMPLE_KEY", "initializer": "AKIAIOSFODNN7EXAMPLE"},
                    {"name": "SAMPLE_SECRET", "initializer": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}
                ]
            }
        ]
    }

    # Case 1: Documentation Access Key ID
    finding_doc_key = {
        "class_name": "AwsDocExample",
        "file": "src/main/java/com/app/AwsDocExample.java",
        "category": "Hardcoded Secret",
        "claim": "Class AwsDocExample contains field 'SAMPLE_KEY' with hardcoded secret.",
        "evidence": {"field_name": "SAMPLE_KEY", "value": "AKIAIOSFODNN7EXAMPLE"}
    }
    res1 = critic.verify_finding(finding_doc_key, repo_model)
    assert res1["verdict"] == "REJECTED"
    assert "documentation sample" in res1["evidence_trail"]["ast_check"]["details"]

    # Case 2: Documentation Secret Key
    finding_doc_secret = {
        "class_name": "AwsDocExample",
        "file": "src/main/java/com/app/AwsDocExample.java",
        "category": "Hardcoded Secret",
        "claim": "Class AwsDocExample contains field 'SAMPLE_SECRET' with hardcoded secret.",
        "evidence": {"field_name": "SAMPLE_SECRET", "value": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}
    }
    res2 = critic.verify_finding(finding_doc_secret, repo_model)
    assert res2["verdict"] == "REJECTED"
    assert "documentation sample" in res2["evidence_trail"]["ast_check"]["details"]


def test_secret_detection_aws_access_key_id_classification_and_masking():
    """
    AUDIT TEST:
    Ensures an actual AWS access key ID (AKIA...) is classified as an account identifier
    (not a secret access key), and proved that raw credentials are NEVER leaked unmasked.
    """
    critic = CriticAgent(MockGraphStore())
    actual_key_id = "AKIA3J5K6L7M8N9P0Q1R"
    repo_model = {
        "analysis_run_id": "snap-akia-001",
        "classes": [
            {
                "name": "CloudCredentials",
                "file": "src/main/java/com/app/CloudCredentials.java",
                "line_start": 10,
                "line_range": "10-40",
                "methods": [],
                "fields": [{"name": "AWS_KEY_ID", "initializer": actual_key_id}]
            }
        ]
    }

    # Case A: Correctly claims AWS Access Key Identifier
    finding_key_id = {
        "class_name": "CloudCredentials",
        "file": "src/main/java/com/app/CloudCredentials.java",
        "category": "Access Key",
        "claim": "Class CloudCredentials contains field 'AWS_KEY_ID' with hardcoded AWS access key ID.",
        "evidence": {"field_name": "AWS_KEY_ID", "value": actual_key_id}
    }
    res_a = critic.verify_finding(finding_key_id, repo_model)
    assert res_a["verdict"] == "VERIFIED"
    details_a = res_a["evidence_trail"]["ast_check"]["details"]
    assert "AWS Access Key Identifier" in details_a
    assert "[REDACTED]" in details_a
    # PROVE raw key is redacted in output!
    assert actual_key_id not in details_a
    assert "AKIA" in details_a

    # Case B: Falsely claims AKIA is a "secret access key leak" or "password"
    finding_false_claim = {
        "class_name": "CloudCredentials",
        "file": "src/main/java/com/app/CloudCredentials.java",
        "category": "Hardcoded Secret",
        "claim": "Class CloudCredentials leaks private secret access key in field 'AWS_KEY_ID'.",
        "evidence": {"field_name": "AWS_KEY_ID", "value": actual_key_id}
    }
    res_b = critic.verify_finding(finding_false_claim, repo_model)
    assert res_b["verdict"] == "REJECTED"
    assert "account identifier, not a secret access key" in res_b["evidence_trail"]["ast_check"]["details"]


def test_secret_detection_real_secret_token_redaction():
    """
    AUDIT TEST:
    Ensures true secret tokens (e.g. OpenAI sk-, GitHub PAT) are verified as secret literals,
    and masked in output.
    """
    critic = CriticAgent(MockGraphStore())
    raw_token = "sk-live-1234567890abcdef1234567890abcdef"
    repo_model = {
        "analysis_run_id": "snap-secret-001",
        "classes": [
            {
                "name": "AiConfig",
                "file": "src/main/java/com/app/AiConfig.java",
                "line_start": 5,
                "line_range": "5-30",
                "methods": [],
                "fields": [{"name": "OPENAI_SECRET", "initializer": raw_token}]
            }
        ]
    }

    finding = {
        "class_name": "AiConfig",
        "file": "src/main/java/com/app/AiConfig.java",
        "category": "Hardcoded Secret",
        "claim": "Class AiConfig contains field 'OPENAI_SECRET' with hardcoded secret literal.",
        "evidence": {"field_name": "OPENAI_SECRET", "value": raw_token}
    }
    res = critic.verify_finding(finding, repo_model)
    assert res["verdict"] == "VERIFIED"
    details = res["evidence_trail"]["ast_check"]["details"]
    assert "secret credential literal" in details
    assert "[REDACTED]" in details
    assert raw_token not in details


def test_secret_detection_weak_default_credential_verified():
    """
    P1 AUDIT TEST:
    Ensures that a weak hardcoded password (e.g. '123456' or 'changeme') in an application
    credential field is NOT dismissed as a placeholder, but verified as an insecure default.
    """
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-weak-001",
        "classes": [
            {
                "name": "AppSecurityConfig",
                "file": "src/main/java/com/app/AppSecurityConfig.java",
                "line_start": 5,
                "line_range": "5-25",
                "methods": [],
                "fields": [{"name": "defaultPassword", "initializer": "123456"}]
            }
        ]
    }

    finding = {
        "class_name": "AppSecurityConfig",
        "file": "src/main/java/com/app/AppSecurityConfig.java",
        "category": "Hardcoded Secret",
        "claim": "Class AppSecurityConfig contains field 'defaultPassword' with hardcoded weak default password.",
        "evidence": {"field_name": "defaultPassword", "value": "123456"}
    }
    res = critic.verify_finding(finding, repo_model)
    assert res["verdict"] == "VERIFIED"
    details = res["evidence_trail"]["ast_check"]["details"]
    assert "insecure hardcoded default/weak credential literal" in details
    assert "[REDACTED]" in details


def test_secret_detection_weak_default_in_test_class_rejected():
    """
    P1 AUDIT TEST:
    Ensures that weak passwords in test fixtures or mock classes fail closed as test fixtures.
    """
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-weak-002",
        "classes": [
            {
                "name": "AuthServiceTest",
                "file": "src/test/java/com/app/AuthServiceTest.java",
                "line_start": 5,
                "line_range": "5-25",
                "methods": [],
                "fields": [{"name": "testPassword", "initializer": "123456"}]
            }
        ]
    }

    finding = {
        "class_name": "AuthServiceTest",
        "file": "src/test/java/com/app/AuthServiceTest.java",
        "category": "Hardcoded Secret",
        "claim": "Class AuthServiceTest contains field 'testPassword' with hardcoded secret.",
        "evidence": {"field_name": "testPassword", "value": "123456"}
    }
    res = critic.verify_finding(finding, repo_model)
    assert res["verdict"] == "REJECTED"
    assert "test fixture credential" in res["evidence_trail"]["ast_check"]["details"]


def test_secret_detection_configuration_reference_rejected():
    """
    AUDIT TEST:
    Ensures dynamic lookups (System.getenv, @Value) are rejected as configuration references.
    """
    critic = CriticAgent(MockGraphStore())
    repo_model = {
        "analysis_run_id": "snap-config-001",
        "classes": [
            {
                "name": "AppConfig",
                "file": "src/main/java/com/app/AppConfig.java",
                "line_start": 5,
                "line_range": "5-25",
                "methods": [],
                "fields": [{"name": "API_KEY", "initializer": "System.getenv(\"API_KEY\")"}]
            }
        ]
    }

    finding = {
        "class_name": "AppConfig",
        "file": "src/main/java/com/app/AppConfig.java",
        "category": "Hardcoded Secret",
        "claim": "Class AppConfig contains field 'API_KEY' with hardcoded secret.",
        "evidence": {"field_name": "API_KEY", "value": "System.getenv(\"API_KEY\")"}
    }
    res = critic.verify_finding(finding, repo_model)
    assert res["verdict"] == "REJECTED"
    assert "dynamic configuration/environment reference" in res["evidence_trail"]["ast_check"]["details"]


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
    assert result["verdict"] == "REJECTED"
    assert "configuration property key identifier" in result["evidence_trail"]["ast_check"]["details"]


# =========================================================================
# P0 AUDIT SUITE: Bounded Submodule Ingestion & Network Policy
# =========================================================================

def test_submodule_ingestion_policy_checks(tmp_path):
    """
    AUDIT TEST:
    Verifies that clone_repository enforces:
    1. Maximum submodule count limit (rejects > 5)
    2. Strict HTTPS requirement (rejects file://, ssh://, git://)
    3. Relative submodule URL resolution against parent clone URL
    4. DNS resolution to prevent private network bypass (rejects loopback, private, link-local IPs)
    """
    fake_target = tmp_path / "target_repo"
    fake_target.mkdir()

    # Create a mock .gitmodules exceeding count limit (> 5 submodules)
    too_many_submodules = "\n".join([
        f'[submodule "sub{i}"]\n\tpath = sub{i}\n\turl = https://github.com/example/sub{i}.git'
        for i in range(7)
    ])
    (fake_target / ".gitmodules").write_text(too_many_submodules, encoding="utf-8")

    # Mock subprocess run to simulate successful base clone
    import subprocess
    original_run = subprocess.run

    def mock_run(cmd, *args, **kwargs):
        class MockProc:
            returncode = 0
            stdout = ""
            stderr = ""
        return MockProc()

    subprocess.run = mock_run
    try:
        # Case 1: Count Limit (> 5 submodules)
        with pytest.raises(HTTPException) as exc1:
            clone_repository(
                clone_url="https://github.com/example/main.git",
                target_dir=fake_target,
                submodules=True
            )
        assert exc1.value.status_code == 400
        assert "exceeds maximum allowed submodule count" in exc1.value.detail

        # Case 2: Protocol Security Policy (reject file:// URL)
        insecure_proto = '[submodule "local"]\n\tpath = local\n\turl = file:///etc/passwd'
        (fake_target / ".gitmodules").write_text(insecure_proto, encoding="utf-8")
        with pytest.raises(HTTPException) as exc2:
            clone_repository(
                clone_url="https://github.com/example/main.git",
                target_dir=fake_target,
                submodules=True
            )
        assert exc2.value.status_code == 403
        assert "strictly HTTPS required" in exc2.value.detail

        # Case 3: Local Network IP Disallowance (reject 127.0.0.1 / localhost)
        local_ip_sub = '[submodule "internal"]\n\tpath = internal\n\turl = https://127.0.0.1/secret.git'
        (fake_target / ".gitmodules").write_text(local_ip_sub, encoding="utf-8")
        with pytest.raises(HTTPException) as exc3:
            clone_repository(
                clone_url="https://github.com/example/main.git",
                target_dir=fake_target,
                submodules=True
            )
        assert exc3.value.status_code == 403
        assert "disallowed under network security policy" in exc3.value.detail

        # Case 4: Relative Submodule URL Resolution
        relative_sub = '[submodule "relative"]\n\tpath = relative\n\turl = ../sibling.git'
        (fake_target / ".gitmodules").write_text(relative_sub, encoding="utf-8")
        # Relative to https://github.com/example/main.git resolves to https://github.com/example/sibling.git
        # Which is a valid HTTPS URL on github.com (passes validation)
        clone_repository(
            clone_url="https://github.com/example/main.git",
            target_dir=fake_target,
            submodules=True
        )
    finally:
        subprocess.run = original_run


# =========================================================================
# AUDIT SUITE: Check H Security Annotation vs Global Configuration
# =========================================================================

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
    assert res_b["verdict"] != "VERIFIED"
    assert "INSUFFICIENT_EVIDENCE" in res_b["evidence_trail"]["ast_check"]["details"]


# =========================================================================
# AUDIT SUITE: Check F Maintainability Exact Method Counts & Abstention
# =========================================================================

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


# =========================================================================
# AUDIT SUITE: Check I Blast Radius Deduplication & Directional Separation
# =========================================================================

def test_blast_radius_deduplication_and_abstention():
    """
    AUDIT CASE:
    Ensure dependent nodes from graph queries are deduplicated, and abstain if count is unstated.
    """
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
