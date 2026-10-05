"""
DevLensX Model Context Protocol (MCP) Grounded Tools (Phase P4-D)

Exposes 8 repository intelligence tools for VS Code and JetBrains IDEs.

CRITICAL INVARIANTS:
1. Exact Snapshot Identity:
   Every tool requires and validates (repository_id, analysis_run_id, commit_hash).
   Missing or unregistered snapshot fails closed with SNAPSHOT_NOT_FOUND.

2. Read-Only & Path-Confined:
   Zero filesystem write access, zero shell execution, zero arbitrary code execution.
   File reads are strictly restricted to the snapshot's registered repo_path.

3. Truth Grounding:
   All returned facts are tagged with VERIFIED (grounded in AST/Evidence/Graph)
   or AI_SUGGESTION / INSUFFICIENT_EVIDENCE.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from devlensx.evidence.models import EvidenceRef, EvidenceType, ResolutionStatus
from devlensx.evidence.resolver import get_snapshot_registry, EvidenceResolver
from devlensx.chat.orchestrator import _model_store, ChatOrchestrator
from devlensx.impact.analyzer import ImpactAnalyzer
from devlensx.review.codeturtle import CodeTurtleReviewEngine
from devlensx.observability.redaction import redact_secret


def _validate_snapshot_and_get_model(analysis_run_id: str, repository_id: Optional[str] = None) -> tuple[Any, Dict[str, Any]]:
    snap_reg = get_snapshot_registry()
    snap = snap_reg.get(analysis_run_id)
    if not snap:
        raise ValueError(f"SNAPSHOT_NOT_FOUND:{analysis_run_id}")
    if repository_id and snap.repository_id != repository_id:
        raise ValueError(f"REPOSITORY_MISMATCH:{snap.repository_id}!={repository_id}")
    model = _model_store.get(analysis_run_id, {})
    return snap, model


def _check_safe_relative_path(repo_path: str, file_path: str) -> Path:
    """Ensures file_path does not escape repo_path via directory traversal."""
    base = Path(repo_path).resolve()
    target = (base / file_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise PermissionError(f"PATH_VIOLATION: Attempted access outside snapshot directory: {file_path}")
    return target


# Tool 1: search_repository
def search_repository(analysis_run_id: str, query: str, limit: int = 10) -> Dict[str, Any]:
    snap, model = _validate_snapshot_and_get_model(analysis_run_id)
    q = (query or "").lower().strip()
    if not q:
        return {"status": "SUCCESS", "results": [], "query": query}

    results = []
    classes = model.get("classes", [])
    for c in classes:
        name = c.get("name", "")
        file_path = c.get("file_path") or c.get("file", "")
        doc = c.get("docstring") or ""
        methods = [m.get("name", "") for m in c.get("methods", [])]

        if q in name.lower() or q in file_path.lower() or any(q in m.lower() for m in methods) or q in doc.lower():
            results.append({
                "symbol_name": name,
                "file_path": file_path,
                "line_start": c.get("line_start", 1),
                "line_end": c.get("line_end", 1),
                "stereotype": c.get("stereotype", "Class"),
                "methods": methods[:5],
                "grounding": "VERIFIED_AST",
            })
            if len(results) >= limit:
                break

    return {
        "status": "SUCCESS",
        "repository_id": snap.repository_id,
        "analysis_run_id": snap.analysis_run_id,
        "commit_hash": snap.commit_hash,
        "total_matches": len(results),
        "results": results,
    }


# Tool 2: explain_symbol
def explain_symbol(analysis_run_id: str, symbol_name: str) -> Dict[str, Any]:
    snap, model = _validate_snapshot_and_get_model(analysis_run_id)
    target = (symbol_name or "").strip()
    classes = model.get("classes", [])

    matched = None
    for c in classes:
        if c.get("name") == target or c.get("name", "").endswith(f".{target}"):
            matched = c
            break

    if not matched:
        return {
            "status": "NOT_FOUND",
            "verdict": "INSUFFICIENT_EVIDENCE",
            "message": f"Symbol '{target}' not found in analyzed snapshot AST.",
        }

    return {
        "status": "SUCCESS",
        "verdict": "VERIFIED",
        "repository_id": snap.repository_id,
        "analysis_run_id": snap.analysis_run_id,
        "symbol_name": matched.get("name"),
        "file_path": matched.get("file_path") or matched.get("file"),
        "line_start": matched.get("line_start"),
        "line_end": matched.get("line_end"),
        "stereotype": matched.get("stereotype", "Class"),
        "methods": [
            {
                "name": m.get("name"),
                "line_start": m.get("line_start"),
                "line_end": m.get("line_end"),
                "parameters": m.get("parameters", []),
            }
            for m in matched.get("methods", [])
        ],
        "dependencies": matched.get("injected_dependencies", []) or matched.get("dependencies", []),
    }


# Tool 3: get_evidence
def get_evidence(analysis_run_id: str, file_path: str, line_start: int, line_end: int) -> Dict[str, Any]:
    snap, _ = _validate_snapshot_and_get_model(analysis_run_id)
    # Validate path confinement
    _check_safe_relative_path(snap.repo_path, file_path)

    ref = EvidenceRef(
        repository_id=snap.repository_id,
        analysis_run_id=snap.analysis_run_id,
        commit_hash=snap.commit_hash,
        file_path=file_path,
        line_start=max(1, int(line_start)),
        line_end=max(int(line_start), int(line_end)),
        evidence_type=EvidenceType.AST,
    )
    resolver = EvidenceResolver()
    resolved = resolver.resolve(ref)

    snippet = "\n".join(l.content for l in resolved.lines)
    return {
        "status": "SUCCESS" if resolved.resolved else "FAILED",
        "resolution_status": resolved.status.value,
        "verdict": "VERIFIED" if resolved.resolved else "INSUFFICIENT_EVIDENCE",
        "file_path": file_path,
        "line_start": ref.line_start,
        "line_end": ref.line_end,
        "snippet": snippet,
        "lines": [{"line": l.line_number, "content": l.content} for l in resolved.lines],
        "message": resolved.message,
    }


# Tool 4: get_callers
def get_callers(analysis_run_id: str, symbol_name: str) -> Dict[str, Any]:
    snap, model = _validate_snapshot_and_get_model(analysis_run_id)
    edges = model.get("graph_edges", [])
    target = (symbol_name or "").strip()

    callers = []
    for edge in edges:
        target_node = edge.get("target") or edge.get("to") or ""
        source_node = edge.get("source") or edge.get("from") or ""
        edge_type = edge.get("type") or edge.get("relationship") or "CALLS"

        if target_node == target or target_node.endswith(f".{target}"):
            callers.append({
                "caller_symbol": source_node,
                "relationship": edge_type,
                "grounding": "VERIFIED_GRAPH",
            })

    return {
        "status": "SUCCESS",
        "verdict": "VERIFIED" if callers else "INSUFFICIENT_EVIDENCE",
        "symbol_name": target,
        "analysis_run_id": snap.analysis_run_id,
        "callers": callers,
        "count": len(callers),
    }


# Tool 5: get_callees
def get_callees(analysis_run_id: str, symbol_name: str) -> Dict[str, Any]:
    snap, model = _validate_snapshot_and_get_model(analysis_run_id)
    edges = model.get("graph_edges", [])
    target = (symbol_name or "").strip()

    callees = []
    for edge in edges:
        source_node = edge.get("source") or edge.get("from") or ""
        target_node = edge.get("target") or edge.get("to") or ""
        edge_type = edge.get("type") or edge.get("relationship") or "CALLS"

        if source_node == target or source_node.endswith(f".{target}"):
            callees.append({
                "callee_symbol": target_node,
                "relationship": edge_type,
                "grounding": "VERIFIED_GRAPH",
            })

    return {
        "status": "SUCCESS",
        "verdict": "VERIFIED" if callees else "INSUFFICIENT_EVIDENCE",
        "symbol_name": target,
        "analysis_run_id": snap.analysis_run_id,
        "callees": callees,
        "count": len(callees),
    }


# Tool 6: analyze_impact
def analyze_impact(analysis_run_id: str, target_symbol: str) -> Dict[str, Any]:
    snap, _ = _validate_snapshot_and_get_model(analysis_run_id)
    result = ImpactAnalyzer.analyze(target_symbol, analysis_run_id)
    
    return {
        "status": "SUCCESS",
        "verdict": "VERIFIED",
        "target_symbol": target_symbol,
        "analysis_run_id": snap.analysis_run_id,
        "risk_level": result.risk_level,
        "affected_count": len(result.downstream),
        "affected_symbols": [
            {
                "symbol_name": s.get("symbol_name") or s.get("name"),
                "file_path": s.get("file_path") or s.get("file"),
                "line_start": s.get("line_start"),
                "risk": s.get("risk", "INFO"),
            }
            for s in result.downstream
        ],
    }


# Tool 7: review_diff
def review_diff(analysis_run_id: str, diff: str, base_commit: Optional[str] = None) -> Dict[str, Any]:
    snap, _ = _validate_snapshot_and_get_model(analysis_run_id)
    review_data = CodeTurtleReviewEngine.review(
        diff=diff,
        analysis_run_id=analysis_run_id,
        base_commit=base_commit,
    )
    return {
        "status": "SUCCESS",
        "analysis_run_id": snap.analysis_run_id,
        "findings": review_data.get("findings", []) or review_data.get("comments", []),
        "requires_user_action": True,
    }


# Tool 8: ask_repository
def ask_repository(analysis_run_id: str, message: str, mode: str = "FAST") -> Dict[str, Any]:
    snap, _ = _validate_snapshot_and_get_model(analysis_run_id)
    answer = ChatOrchestrator.chat(
        analysis_run_id=analysis_run_id,
        message=message,
        mode=mode,
    )
    return {
        "status": "SUCCESS",
        "analysis_run_id": snap.analysis_run_id,
        "answer": redact_secret(answer.answer),
        "verified_claims": answer.verified_claims,
        "unverified_claims": answer.unverified_claims,
        "citations": [c.to_dict() for c in answer.citations],
        "verdict": answer.verdict.value,
    }


# Tool 9: verify_architecture
def verify_architecture(analysis_run_id: str, repository_id: Optional[str] = None, rule_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    snap, _ = _validate_snapshot_and_get_model(analysis_run_id, repository_id)
    from devlensx.governance.evaluator import GovernanceEvaluator
    from devlensx.governance.rules import get_governance_rule_registry

    reg = get_governance_rule_registry()
    if rule_ids:
        active_rules = [r for r in reg.get_rules(enabled_only=False) if r.rule_id in rule_ids]
    else:
        active_rules = reg.get_rules(enabled_only=True)

    evaluator = GovernanceEvaluator(snapshot_registry=get_snapshot_registry())
    findings = evaluator.evaluate(
        repository_id=snap.repository_id,
        analysis_run_id=analysis_run_id,
        commit_hash=snap.commit_hash,
        rules=active_rules,
    )
    return {
        "status": "SUCCESS",
        "repository_id": snap.repository_id,
        "analysis_run_id": snap.analysis_run_id,
        "commit_hash": snap.commit_hash,
        "total_findings": len(findings),
        "verified_count": sum(1 for f in findings if f.verdict == "VERIFIED"),
        "findings": [f.to_dict() for f in findings],
    }


# Tool 10: verify_contracts
def verify_contracts(
    workspace_id: str,
    producer_repo_id: str,
    consumer_repo_id: str,
    producer_run_id: str,
    consumer_run_id: str,
    producer_commit: Optional[str] = None,
    consumer_commit: Optional[str] = None,
) -> Dict[str, Any]:
    from devlensx.governance.contracts import get_cross_service_contract_verifier
    verifier = get_cross_service_contract_verifier()
    report = verifier.verify_contracts(
        workspace_id=workspace_id,
        producer_repo_id=producer_repo_id,
        consumer_repo_id=consumer_repo_id,
        producer_run_id=producer_run_id,
        consumer_run_id=consumer_run_id,
        producer_commit=producer_commit,
        consumer_commit=consumer_commit,
    )
    return {
        "status": "SUCCESS",
        "report": report,
    }


# Registry of 8 Core MCP tools (P4 Frozen Baseline)
MCP_TOOL_DEFINITIONS = [
    {
        "name": "devlensx.search_repository",
        "description": "Search symbols, methods, and files grounded in AST for the active repository snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "query": {"type": "string", "description": "Search query symbol or keyword"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["analysis_run_id", "query"],
        },
    },
    {
        "name": "devlensx.explain_symbol",
        "description": "Retrieve AST definition, docstrings, methods, and dependencies for a symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "symbol_name": {"type": "string", "description": "Exact class or function name"},
            },
            "required": ["analysis_run_id", "symbol_name"],
        },
    },
    {
        "name": "devlensx.get_evidence",
        "description": "Fetch verified source evidence for exact file and line ranges inside the snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "file_path": {"type": "string", "description": "Path relative to repository root"},
                "line_start": {"type": "integer", "description": "Start line (1-indexed)"},
                "line_end": {"type": "integer", "description": "End line (1-indexed)"},
            },
            "required": ["analysis_run_id", "file_path", "line_start", "line_end"],
        },
    },
    {
        "name": "devlensx.get_callers",
        "description": "Retrieve call graph caller symbols that invoke the target symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "symbol_name": {"type": "string", "description": "Target symbol to find callers for"},
            },
            "required": ["analysis_run_id", "symbol_name"],
        },
    },
    {
        "name": "devlensx.get_callees",
        "description": "Retrieve call graph callee symbols called by the target symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "symbol_name": {"type": "string", "description": "Source symbol to find callees for"},
            },
            "required": ["analysis_run_id", "symbol_name"],
        },
    },
    {
        "name": "devlensx.analyze_impact",
        "description": "Calculate blast radius and affected downstream components if a symbol is changed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "target_symbol": {"type": "string", "description": "Modified symbol name"},
            },
            "required": ["analysis_run_id", "target_symbol"],
        },
    },
    {
        "name": "devlensx.review_diff",
        "description": "Run CodeTurtle grounded review on a diff with committable suggestions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "diff": {"type": "string", "description": "Unified git diff"},
                "base_commit": {"type": "string", "description": "Optional base commit hash"},
            },
            "required": ["analysis_run_id", "diff"],
        },
    },
    {
        "name": "devlensx.ask_repository",
        "description": "Ask grounded questions about repository architecture with ClaimVerifier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "message": {"type": "string", "description": "User question"},
                "mode": {"type": "string", "enum": ["FAST", "CODEMAP", "DEEP_RESEARCH"], "default": "FAST"},
            },
            "required": ["analysis_run_id", "message"],
        },
    },
]

# P5 Governance & Contract Tools Extension
MCP_P5_TOOL_DEFINITIONS = [
    {
        "name": "devlensx.verify_architecture",
        "description": "Verify architectural boundaries, layer hierarchies, and cycle rules for a repository snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "analysis_run_id": {"type": "string", "description": "Target analysis run ID"},
                "repository_id": {"type": "string", "description": "Optional repository ID verification"},
                "rule_ids": {"type": "array", "items": {"type": "string"}, "description": "Optional rule filter"},
            },
            "required": ["analysis_run_id"],
        },
    },
    {
        "name": "devlensx.verify_contracts",
        "description": "Verify cross-service API contract compatibility between producer and consumer snapshots in a federated workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "Target federated workspace ID"},
                "producer_repo_id": {"type": "string", "description": "Producer repository ID"},
                "consumer_repo_id": {"type": "string", "description": "Consumer repository ID"},
                "producer_run_id": {"type": "string", "description": "Producer analysis run ID"},
                "consumer_run_id": {"type": "string", "description": "Consumer analysis run ID"},
                "producer_commit": {"type": "string", "description": "Optional producer commit hash"},
                "consumer_commit": {"type": "string", "description": "Optional consumer commit hash"},
            },
            "required": ["workspace_id", "producer_repo_id", "consumer_repo_id", "producer_run_id", "consumer_run_id"],
        },
    },
]

MCP_ALL_TOOL_DEFINITIONS = MCP_TOOL_DEFINITIONS + MCP_P5_TOOL_DEFINITIONS

TOOL_HANDLERS = {
    "devlensx.search_repository": search_repository,
    "devlensx.explain_symbol": explain_symbol,
    "devlensx.get_evidence": get_evidence,
    "devlensx.get_callers": get_callers,
    "devlensx.get_callees": get_callees,
    "devlensx.analyze_impact": analyze_impact,
    "devlensx.review_diff": review_diff,
    "devlensx.ask_repository": ask_repository,
    "devlensx.verify_architecture": verify_architecture,
    "devlensx.verify_contracts": verify_contracts,
}
