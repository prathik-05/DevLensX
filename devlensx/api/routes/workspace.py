"""DevLensX Workspace API Routes (D9)"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from devlensx.workspace.session import get_workspace_registry
from devlensx.workspace.orchestrator import UnifiedWorkspaceOrchestrator
from devlensx.impact.analyzer import ImpactAnalyzer
from devlensx.build.planner import BuildPlanner
from devlensx.debug.stacktrace import StackTraceParser
from devlensx.review.review_engine import ReviewEngine
from devlensx.chat.orchestrator import ChatOrchestrator
from devlensx.workspace.session import get_workspace_registry
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.understanding.model.repository_brain import RepositoryBrain

router = APIRouter(prefix="/api/workspace", tags=["Workspace"])


class WorkspaceSessionRequest(BaseModel):
    analysis_run_id: str
    repository_id: Optional[str] = None
    commit_hash: Optional[str] = None


class WorkspaceContextUpdate(BaseModel):
    active_page: Optional[str] = None
    active_section: Optional[str] = None
    active_symbol: Optional[str] = None
    active_diagram: Optional[str] = None
    current_task: Optional[str] = None
    mode: Optional[str] = None
    selected_files: Optional[List[str]] = None
    selected_evidence: Optional[List[Dict[str, Any]]] = None


class ImpactRequest(BaseModel):
    target_symbol: str
    repository_id: Optional[str] = None


class BuildPlanRequest(BaseModel):
    task: str
    target_symbol: Optional[str] = None


class DebugTraceRequest(BaseModel):
    stack_trace: str


class ReviewDiffRequest(BaseModel):
    diff: str
    base_commit: Optional[str] = None
    custom_prompt: Optional[str] = None
    provider: Optional[str] = "auto"
    api_key: Optional[str] = None
    azure_config: Optional[Dict[str, str]] = None
    analysis_run_id: Optional[str] = None


@router.post("/session")
def create_workspace_session(req: WorkspaceSessionRequest):
    """Create or retrieve a workspace session for an analysis run."""
    from devlensx.workspace.orchestrator import UnifiedWorkspaceOrchestrator
    result = UnifiedWorkspaceOrchestrator.ensure_session(req.analysis_run_id)
    if not result["valid"]:
        raise HTTPException(status_code=404, detail=result.get("status", "UNKNOWN_RUN"))
    return result


@router.get("/{analysis_run_id}/context")
def get_workspace_context(analysis_run_id: str):
    """Get current workspace context for an analysis run."""
    result = UnifiedWorkspaceOrchestrator.validate_snapshot(analysis_run_id)
    if not result["valid"]:
        raise HTTPException(status_code=404, detail=result.get("status", "UNKNOWN_RUN"))
    return result


@router.post("/{analysis_run_id}/context")
def update_workspace_context(analysis_run_id: str, req: WorkspaceContextUpdate):
    """Update workspace context (page, section, symbol, etc.)"""
    result = UnifiedWorkspaceOrchestrator.update_context(analysis_run_id, req.dict(exclude_none=True))
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result.get("status", "INVALID"))
    return result


@router.post("/{analysis_run_id}/impact")
def get_change_impact(analysis_run_id: str, req: ImpactRequest):
    """Calculate change impact for a target symbol."""
    from devlensx.workspace.orchestrator import UnifiedWorkspaceOrchestrator
    from devlensx.evidence.resolver import get_snapshot_registry
    from devlensx.understanding.model.repository_brain import RepositoryBrain
    
    snap = get_snapshot_registry().get(analysis_run_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Unknown analysis run")
    
    try:
        impact = ImpactAnalyzer.analyze(req.target_symbol, analysis_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return {
        "repository_id": impact.repository_id,
        "analysis_run_id": impact.analysis_run_id,
        "commit_hash": impact.commit_hash,
        "target_symbol": impact.target_symbol,
        "status": impact.status,
        "risk_level": impact.risk_level,
        "impact": {
            "directly_affected": len(impact.downstream),
            "potentially_affected": len(impact.downstream) + len(impact.tests),
        },
        "direct": impact.direct,
        "downstream": impact.downstream,
        "tests": impact.tests,
        "configs": impact.configs,
        "evidence_refs": impact.evidence_refs,
        "diagram": impact.diagram,
    }


@router.post("/{analysis_run_id}/build/plan")
def create_build_plan(analysis_run_id: str, req: BuildPlanRequest):
    """Generate a change plan with evidence-backed steps."""
    from devlensx.build.planner import BuildPlanner
    try:
        plan = BuildPlanner.plan(req.task, req.target_symbol or "", analysis_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return plan.to_dict()


@router.post("/{analysis_run_id}/debug/trace")
def debug_stack_trace(analysis_run_id: str, req: DebugTraceRequest):
    """Parse stack trace and map to verified source locations."""
    try:
        result = StackTraceParser.parse(req.stack_trace, analysis_run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/{analysis_run_id}/review/diff")
def review_diff(analysis_run_id: str, req: ReviewDiffRequest):
    """Analyze git diff and produce evidence-grounded review findings.

    P1-C: optional base_commit establishes diff-base vs snapshot
    compatibility (EXACT_SNAPSHOT vs BASE_MISMATCH).
    """
    try:
        result = ReviewEngine.review(req.diff, analysis_run_id, req.base_commit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/{analysis_run_id}/review/codeturtle")
def review_codeturtle(analysis_run_id: str, req: ReviewDiffRequest):
    """Analyze git diff with CodeTurtle AI code reviewer and PR auditor for an exact snapshot."""
    from devlensx.review.codeturtle import CodeTurtleReviewEngine
    try:
        return CodeTurtleReviewEngine.review(
            diff=req.diff,
            analysis_run_id=analysis_run_id,
            base_commit=req.base_commit,
            custom_prompt=req.custom_prompt,
            provider=req.provider or "auto",
            api_key=req.api_key or "",
            azure_config=req.azure_config,
        )
    except ValueError as e:
        err_msg = str(e)
        if "SNAPSHOT_NOT_FOUND" in err_msg or "UNKNOWN_RUN" in err_msg:
            raise HTTPException(status_code=404, detail=f"SNAPSHOT_NOT_FOUND:{analysis_run_id}")
        if "SNAPSHOT_UNAVAILABLE" in err_msg or "MODEL_EVICTED" in err_msg:
            raise HTTPException(status_code=404, detail=f"SNAPSHOT_UNAVAILABLE:{analysis_run_id}")
        raise HTTPException(status_code=400, detail=err_msg)


@router.post("/{analysis_run_id}/review/coderabbit")
def review_coderabbit_alias(analysis_run_id: str, req: ReviewDiffRequest):
    """Compatibility alias forwarding directly to CodeTurtle review."""
    return review_codeturtle(analysis_run_id, req)


@router.post("/review/codeturtle")
def review_codeturtle_global(req: ReviewDiffRequest):
    """Global CodeTurtle review endpoint with analysis_run_id in body."""
    run_id = req.analysis_run_id
    if not run_id:
        raise HTTPException(status_code=400, detail="analysis_run_id is required in request body.")
    return review_codeturtle(run_id, req)


@router.post("/review/coderabbit")
def review_coderabbit_global_alias(req: ReviewDiffRequest):
    """Compatibility alias forwarding directly to global CodeTurtle review."""
    return review_codeturtle_global(req)


# Context propagation for D8 Chat
@router.post("/{analysis_run_id}/chat")
def chat_in_workspace(analysis_run_id: str, req: dict):
    """Chat with context from current workspace."""
    from devlensx.chat.orchestrator import ChatOrchestrator
    from devlensx.workspace.session import get_workspace_registry
    from devlensx.evidence.resolver import get_snapshot_registry
    
    snap = get_snapshot_registry().get(analysis_run_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Unknown analysis run")
    
    reg = get_workspace_registry()
    sess = get_workspace_registry().get(analysis_run_id) or reg.create_or_get(analysis_run_id)
    ctx = reg.to_context(sess) if hasattr(reg, 'to_context') else None
    
    # Merge workspace context with request context
    req_context = req.get("context", {})
    if ctx:
        # Workspace context takes precedence for snapshot-bound fields
        merged_context = {
            "page_id": ctx.page_id or req_context.get("page_id"),
            "section_id": ctx.section_id or req_context.get("section_id"),
            "diagram_id": ctx.diagram_id or req_context.get("diagram_id"),
            "selected_symbol": ctx.symbol_id or req_context.get("selected_symbol") or req_context.get("symbol_id"),
            "selected_file": req_context.get("selected_file"),
            "selected_lines": req_context.get("selected_lines"),
        }
        req_context = {k: v for k, v in merged_context.items() if v is not None}
    
    try:
        ans = ChatOrchestrator.chat(analysis_run_id, req.get("message", ""), mode=req.get("mode", "FAST"), context=req_context)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ans.to_dict()


# Context update from UI
@router.post("/{analysis_run_id}/context/update")
def update_workspace_context(analysis_run_id: str, req: dict):
    """Update workspace context (page, section, symbol, etc.) and emit event."""
    from devlensx.workspace.orchestrator import UnifiedWorkspaceOrchestrator
    result = UnifiedWorkspaceOrchestrator.update_context(analysis_run_id, req)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result.get("status", "INVALID"))
    return result


# Snapshot validation
@router.get("/{analysis_run_id}/validate")
def validate_snapshot(analysis_run_id: str, repository_id: Optional[str] = None, commit_hash: Optional[str] = None):
    """Validate snapshot integrity and freshness.

    UNKNOWN_RUN -> 404 (nothing to show).
    REPOSITORY_MISMATCH / STALE / STALE_COMMIT -> 200 with valid:false
    so the UI can render the stale state + [Re-analyze] action.
    """
    result = UnifiedWorkspaceOrchestrator.validate_snapshot(analysis_run_id, repository_id, commit_hash)
    if result.get("status") == "UNKNOWN_RUN":
        raise HTTPException(status_code=404, detail="UNKNOWN_RUN")
    return result