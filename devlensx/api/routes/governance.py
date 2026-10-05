"""
DevLensX Architectural Governance & Contract Verification REST API (Phase P5)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from devlensx.governance.models import ArchitecturalRule, GovernanceFinding
from devlensx.governance.rules import get_governance_rule_registry
from devlensx.governance.evaluator import GovernanceEvaluator
from devlensx.governance.contracts import get_cross_service_contract_verifier
from devlensx.evidence.resolver import get_snapshot_registry

router = APIRouter(prefix="/api/governance", tags=["Architectural Governance"])


class RuleDefinitionRequest(BaseModel):
    rule_id: str
    name: str
    rule_type: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    source_selector: Dict[str, Any] = Field(default_factory=dict)
    target_selector: Optional[Dict[str, Any]] = None
    constraint: str = "FORBIDDEN"
    severity: str = "WARNING"
    description: str = ""
    enabled: bool = True


class GovernanceEvaluateRequest(BaseModel):
    analysis_run_id: str
    repository_id: Optional[str] = None
    commit_hash: Optional[str] = None
    rule_ids: Optional[List[str]] = None


class ContractVerifyRequest(BaseModel):
    workspace_id: str
    producer_repo_id: str
    consumer_repo_id: str
    producer_run_id: str
    consumer_run_id: str
    producer_commit: Optional[str] = None
    consumer_commit: Optional[str] = None


@router.get("/rules")
def list_rules(enabled_only: bool = True):
    """Retrieve all registered architectural governance rules."""
    registry = get_governance_rule_registry()
    rules = registry.get_rules(enabled_only=enabled_only)
    return {"rules": [r.to_dict() for r in rules]}


@router.post("/rules")
def register_or_update_rule(req: RuleDefinitionRequest):
    """Register or update an architectural governance rule."""
    rule = ArchitecturalRule(
        rule_id=req.rule_id,
        name=req.name,
        rule_type=req.rule_type,
        scope=req.scope,
        source_selector=req.source_selector,
        target_selector=req.target_selector,
        constraint=req.constraint,
        severity=req.severity,
        description=req.description,
        enabled=req.enabled,
    )
    get_governance_rule_registry().register_rule(rule)
    return {"valid": True, "rule": rule.to_dict()}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str):
    """Remove a rule from the active registry."""
    deleted = get_governance_rule_registry().remove_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    return {"valid": True, "rule_id": rule_id}


@router.post("/rules/reset")
def reset_rules():
    """Reset the registry to built-in canonical defaults."""
    get_governance_rule_registry().reset_defaults()
    return {"valid": True, "message": "Rules reset to default."}


@router.post("/evaluate")
def evaluate_snapshot_governance(req: GovernanceEvaluateRequest):
    """
    Evaluates active governance rules against an immutable snapshot.
    Guarantees truth boundary: only grounded EvidenceRefs receive VERIFIED verdict.
    """
    snap_reg = get_snapshot_registry()
    run_id = req.analysis_run_id

    # Fallback to active run if not supplied or empty
    if not run_id:
        try:
            from devlensx.api.main import global_state
            run_id = global_state.get("analysis_run_id")
        except Exception:
            pass

    if not run_id:
        raise HTTPException(
            status_code=400,
            detail="NO_ACTIVE_ANALYSIS: No active analysis snapshot found. Run an analysis first or click 'Load Demo Data'."
        )

    snap = snap_reg.get(run_id)
    if not snap:
        # Check global_state recovery
        try:
            from devlensx.api.main import global_state
            repo_model = global_state.get("repo_model") or {}
            if repo_model:
                r_id = repo_model.get("repo") or req.repository_id or "repository"
                r_path = repo_model.get("repo_path") or "."
                from devlensx.evidence import register_snapshot
                snap = register_snapshot(
                    repository_id=r_id,
                    analysis_run_id=run_id,
                    repo_path=r_path,
                    commit_hash=repo_model.get("commit_hash"),
                )
        except Exception:
            pass

    if not snap:
        raise HTTPException(status_code=404, detail=f"SNAPSHOT_NOT_FOUND:{run_id}")

    repo_id = req.repository_id or snap.repository_id

    # Path-tolerant repository name matching
    def _norm(name: str) -> str:
        import os
        return os.path.basename(name.replace("\\", "/").rstrip("/")).lower() if name else ""

    if _norm(snap.repository_id) and _norm(repo_id) and _norm(snap.repository_id) != _norm(repo_id):
        raise HTTPException(
            status_code=400,
            detail=f"REPOSITORY_MISMATCH:{snap.repository_id}!={repo_id}"
        )

    registry = get_governance_rule_registry()
    if req.rule_ids:
        active_rules = [r for r in registry.get_rules(enabled_only=False) if r.rule_id in req.rule_ids]
    else:
        active_rules = registry.get_rules(enabled_only=True)

    evaluator = GovernanceEvaluator(snapshot_registry=snap_reg)
    findings = evaluator.evaluate(
        repository_id=snap.repository_id,
        analysis_run_id=run_id,
        commit_hash=req.commit_hash or snap.commit_hash,
        rules=active_rules,
    )

    verified_count = sum(1 for f in findings if f.verdict == "VERIFIED")
    suggestion_count = sum(1 for f in findings if f.verdict == "AI_SUGGESTION")
    insufficient_count = sum(1 for f in findings if f.verdict == "INSUFFICIENT_EVIDENCE")

    return {
        "valid": True,
        "repository_id": snap.repository_id,
        "analysis_run_id": run_id,
        "commit_hash": req.commit_hash or snap.commit_hash,
        "total_findings": len(findings),
        "verified_count": verified_count,
        "suggestion_count": suggestion_count,
        "insufficient_evidence_count": insufficient_count,
        "findings": [f.to_dict() for f in findings],
    }


@router.post("/contracts/verify")
def verify_cross_service_contracts(req: ContractVerifyRequest):
    """
    Validates API contracts between producer and consumer services across federated boundaries.
    """
    verifier = get_cross_service_contract_verifier()
    ws_mgr = verifier.workspace_manager

    # Auto-provision workspace if missing
    ws = ws_mgr.get_workspace(req.workspace_id)
    if not ws:
        ws = ws_mgr.create_workspace(req.workspace_id, f"Auto-provisioned {req.workspace_id}")

    if req.producer_repo_id not in ws.repositories:
        ws_mgr.add_repository(req.workspace_id, req.producer_repo_id)
    if req.consumer_repo_id not in ws.repositories:
        ws_mgr.add_repository(req.workspace_id, req.consumer_repo_id)

    try:
        report = verifier.verify_contracts(
            workspace_id=req.workspace_id,
            producer_repo_id=req.producer_repo_id,
            consumer_repo_id=req.consumer_repo_id,
            producer_run_id=req.producer_run_id,
            consumer_run_id=req.consumer_run_id,
            producer_commit=req.producer_commit,
            consumer_commit=req.consumer_commit,
        )
        return {"valid": True, "report": report}
    except ValueError as e:
        err_msg = str(e)
        status_code = 404 if "NOT_FOUND" in err_msg else 400
        raise HTTPException(status_code=status_code, detail=err_msg)


@router.post("/demo/seed")
def seed_governance_demo():
    """
    Seeds canonical demonstration data for both Architectural Rules and Cross-Service Contracts.
    Enables immediate 1-click exploration and testing with zero manual setup.
    """
    from devlensx.chat.orchestrator import _model_store
    snap_reg = get_snapshot_registry()

    # 1. Architectural Rules Demo Snapshot
    demo_repo = "demo-eshop-service"
    demo_run = "run-demo-eshop-001"
    demo_commit = "c0ffee123456"

    snap_reg.register(demo_repo, demo_run, "/demo/eshop", demo_commit)

    demo_model = {
        "repo": demo_repo,
        "classes": [
            {
                "name": "OrderController",
                "stereotype": "Controller",
                "package": "com.eshop.web",
                "file": "src/com/eshop/web/OrderController.java",
                "line_start": 24,
                "line_end": 75,
                "injected_dependencies": ["OrderDao", "OrderService"],
            },
            {
                "name": "OrderDao",
                "stereotype": "Repository",
                "package": "com.eshop.db",
                "file": "src/com/eshop/db/OrderDao.java",
                "line_start": 10,
                "line_end": 45,
                "injected_dependencies": [],
            },
            {
                "name": "OrderService",
                "stereotype": "Service",
                "package": "com.eshop.service",
                "file": "src/com/eshop/service/OrderService.java",
                "line_start": 18,
                "line_end": 90,
                "injected_dependencies": ["PaymentService"],
            },
            {
                "name": "PaymentService",
                "stereotype": "Service",
                "package": "com.eshop.service",
                "file": "src/com/eshop/service/PaymentService.java",
                "line_start": 15,
                "line_end": 80,
                "injected_dependencies": ["OrderService"],
            },
        ],
        "graph_edges": [
            {"source": "OrderController", "target": "OrderDao", "type": "calls"},
            {"source": "OrderController", "target": "OrderService", "type": "calls"},
            {"source": "OrderService", "target": "PaymentService", "type": "calls"},
            {"source": "PaymentService", "target": "OrderService", "type": "calls"},
        ],
    }
    _model_store[demo_run] = demo_model

    # 2. Cross-Service Contract Demo
    verifier = get_cross_service_contract_verifier()
    ws_mgr = verifier.workspace_manager

    ws_id = "ws-ecommerce"
    ws = ws_mgr.get_workspace(ws_id)
    if not ws:
        ws = ws_mgr.create_workspace(ws_id, "E-Commerce Microservices Workspace")

    prod_repo = "orders-service"
    cons_repo = "gateway-client"
    prod_run = "run-prod-v2"
    cons_run = "run-cons-v1"

    if prod_repo not in ws.repositories:
        ws_mgr.add_repository(ws_id, prod_repo)
    if cons_repo not in ws.repositories:
        ws_mgr.add_repository(ws_id, cons_repo)

    snap_reg.register(prod_repo, prod_run, "/demo/orders", "prod-hash-002")
    snap_reg.register(cons_repo, cons_run, "/demo/gateway", "cons-hash-001")

    # Producer V2: Removed /api/v1/orders/cancel (BREAKING)
    _model_store[prod_run] = {
        "endpoints": [
            {
                "path": "/api/v1/orders",
                "http_method": "POST",
                "parameters": {"customerId": {"type": "string", "required": True}},
                "status_codes": [201],
            },
            {
                "path": "/api/v1/orders/{orderId}",
                "http_method": "GET",
                "parameters": {"orderId": {"type": "string", "required": True}},
                "status_codes": [200],
            },
        ]
    }

    # Consumer V1: expects /api/v1/orders, /api/v1/orders/{orderId}, and /api/v1/orders/cancel
    _model_store[cons_run] = {
        "client_endpoints": [
            {
                "path": "/api/v1/orders",
                "http_method": "POST",
                "parameters": {"customerId": {"type": "string", "required": True}},
                "status_codes": [201],
            },
            {
                "path": "/api/v1/orders/{orderId}",
                "http_method": "GET",
                "parameters": {"orderId": {"type": "string", "required": True}},
                "status_codes": [200],
            },
            {
                "path": "/api/v1/orders/cancel",
                "http_method": "POST",
                "parameters": {"orderId": {"type": "string", "required": True}},
                "status_codes": [200],
            },
        ]
    }

    return {
        "valid": True,
        "rules_demo": {
            "repository_id": demo_repo,
            "analysis_run_id": demo_run,
            "commit_hash": demo_commit,
        },
        "contracts_demo": {
            "workspace_id": ws_id,
            "producer_repo_id": prod_repo,
            "consumer_repo_id": cons_repo,
            "producer_run_id": prod_run,
            "consumer_run_id": cons_run,
        }
    }

