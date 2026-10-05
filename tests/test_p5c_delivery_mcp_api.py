"""
Tests for Phase P5-C: Delivery Integrations (MCP Tools, CodeTurtle, REST API).

Validates:
1. MCP tool devlensx.verify_architecture.
2. MCP tool devlensx.verify_contracts.
3. CodeTurtle PR review surfaces grounded architectural violations.
4. FastAPI endpoints under /api/governance/.
"""

import pytest
from fastapi.testclient import TestClient

from devlensx.api.main import app
from devlensx.mcp.tools import verify_architecture, verify_contracts
from devlensx.chat.orchestrator import _model_store
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.workspace.federation import get_federated_workspace_manager, reset_federated_workspace_manager
from devlensx.review.codeturtle import CodeTurtleReviewEngine


@pytest.fixture(autouse=True)
def setup_teardown():
    reset_federated_workspace_manager()
    yield
    reset_federated_workspace_manager()


def test_mcp_verify_architecture():
    snap_reg = get_snapshot_registry()
    snap_reg.register("repo-arch", "run-mcp-arch", "/path/mcp", "hash-mcp")

    _model_store["run-mcp-arch"] = {
        "classes": [
            {
                "name": "OrderController",
                "stereotype": "Controller",
                "injected_dependencies": ["OrderRepository"],
                "file": "OrderController.java",
                "line_start": 5,
            },
            {
                "name": "OrderRepository",
                "stereotype": "Repository",
                "file": "OrderRepository.java",
                "line_start": 1,
            }
        ],
        "graph_edges": []
    }

    res = verify_architecture(analysis_run_id="run-mcp-arch")
    assert res["status"] == "SUCCESS"
    assert res["repository_id"] == "repo-arch"
    assert res["total_findings"] >= 1
    # Check rule ARCH-001 violation
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "ARCH-001" in rule_ids


def test_mcp_verify_contracts():
    snap_reg = get_snapshot_registry()
    ws_mgr = get_federated_workspace_manager()

    ws_mgr.create_workspace("ws-mcp")
    ws_mgr.add_repository("ws-mcp", "svc-orders", "Orders API", "/path/orders")
    ws_mgr.add_repository("ws-mcp", "svc-gateway", "Gateway", "/path/gateway")

    snap_reg.register("svc-orders", "run-orders-1", "/path/orders", "hash-ord")
    snap_reg.register("svc-gateway", "run-gateway-1", "/path/gateway", "hash-gw")

    _model_store["run-orders-1"] = {
        "endpoints": [
            {"path": "/orders", "http_method": "GET", "parameters": {}}
        ]
    }
    _model_store["run-gateway-1"] = {
        "client_endpoints": [
            {"path": "/orders", "http_method": "GET", "parameters": {}}
        ]
    }

    res = verify_contracts(
        workspace_id="ws-mcp",
        producer_repo_id="svc-orders",
        consumer_repo_id="svc-gateway",
        producer_run_id="run-orders-1",
        consumer_run_id="run-gateway-1",
    )
    assert res["status"] == "SUCCESS"
    assert res["report"]["is_compatible"] is True


def test_fastapi_governance_routes():
    client = TestClient(app)

    # 1. GET /api/governance/rules
    res = client.get("/api/governance/rules")
    assert res.status_code == 200
    data = res.json()
    assert "rules" in data
    assert any(r["rule_id"] == "ARCH-001" for r in data["rules"])

    # 2. POST /api/governance/rules
    new_rule = {
        "rule_id": "CUSTOM-001",
        "name": "Custom Test Rule",
        "rule_type": "FORBIDDEN_DEPENDENCY",
        "source_selector": {"stereotype": "Service"},
        "target_selector": {"stereotype": "Controller"},
        "constraint": "FORBIDDEN",
        "severity": "CRITICAL",
        "enabled": True,
    }
    res = client.post("/api/governance/rules", json=new_rule)
    assert res.status_code == 200
    assert res.json()["valid"] is True

    # 3. POST /api/governance/rules/reset
    res = client.post("/api/governance/rules/reset")
    assert res.status_code == 200

    # 4. POST /api/governance/evaluate on registered snapshot
    snap_reg = get_snapshot_registry()
    snap_reg.register("repo-api-test", "run-api-eval-1", "/path/test", "hash-api-eval")
    _model_store["run-api-eval-1"] = {
        "classes": [
            {
                "name": "APIController",
                "stereotype": "Controller",
                "injected_dependencies": ["APIRepository"],
                "file": "APIController.java",
                "line_start": 10,
            },
            {
                "name": "APIRepository",
                "stereotype": "Repository",
                "file": "APIRepository.java",
                "line_start": 5,
            }
        ],
        "graph_edges": []
    }

    eval_req = {
        "analysis_run_id": "run-api-eval-1",
        "repository_id": "repo-api-test",
    }
    res = client.post("/api/governance/evaluate", json=eval_req)
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is True
    assert body["total_findings"] >= 1
    # Unknown snapshot fails closed
    res_bad = client.post("/api/governance/evaluate", json={"analysis_run_id": "ghost-run"})
    assert res_bad.status_code == 404


def test_codeturtle_governance_review_integration():
    snap_reg = get_snapshot_registry()
    snap_reg.register("repo-turtle", "run-turtle-gov", "/path/turtle", "hash-turtle")

    _model_store["run-turtle-gov"] = {
        "classes": [
            {
                "name": "PaymentController",
                "stereotype": "Controller",
                "injected_dependencies": ["PaymentRepository"],
                "file": "PaymentController.java",
                "line_start": 12,
            },
            {
                "name": "PaymentRepository",
                "stereotype": "Repository",
                "file": "PaymentRepository.java",
                "line_start": 4,
            }
        ],
        "graph_edges": []
    }

    diff = (
        "diff --git a/PaymentController.java b/PaymentController.java\n"
        "index 1234567..89abcdef 100644\n"
        "--- a/PaymentController.java\n"
        "+++ b/PaymentController.java\n"
        "@@ -10,3 +10,4 @@\n"
        " class PaymentController {\n"
        "+    @Autowired PaymentRepository paymentRepository;\n"
        " }\n"
    )

    result = CodeTurtleReviewEngine.review(
        diff=diff,
        analysis_run_id="run-turtle-gov",
        provider="none",  # Deterministic grounding only
    )

    comments = result.get("comments", [])
    arch_comments = [c for c in comments if c.get("category") == "Architecture"]
    assert len(arch_comments) >= 1
    assert "ARCH-001" in arch_comments[0].get("rule_id", "")
    assert "intermediate Service" in arch_comments[0].get("suggested_fix", "")
