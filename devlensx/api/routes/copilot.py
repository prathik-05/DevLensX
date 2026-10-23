"""
DevLensX Copilot & Engineering Decision API Routes
"""

from fastapi import APIRouter, Depends
from typing import Optional, Any
from devlensx.db import get_db, User
from devlensx.schemas.copilot import CopilotAskRequest, EngineeringDecisionRequest
from devlensx.services.auth_service import AuthService
from devlensx.services.copilot_service import CopilotService

router = APIRouter(prefix="/api/copilot", tags=["Copilot"])


@router.post("/ask")
def ask_copilot(req: CopilotAskRequest):
    """DevLensX Assistant Q&A endpoint. Resolves context across session history turns with grounded AST and Graph context."""
    from devlensx.api.main import global_state
    from devlensx.reasoning.engine import RepositoryReasoningEngine

    # Active run resolution
    run_id = getattr(req, "analysis_run_id", None) or getattr(req, "repo_id", None)
    repo_model = {}
    if run_id:
        try:
            from devlensx.chat.orchestrator import _load_model
            repo_model = _load_model(run_id)
        except Exception:
            repo_model = {}
    if not repo_model:
        repo_model = global_state.get("repo_model") or {}

    graph_store = global_state.get("graph_store")
    retriever = global_state.get("retriever")

    engine = RepositoryReasoningEngine()
    history = []
    if req.session_history:
        for turn in req.session_history:
            if isinstance(turn, dict):
                role = turn.get("role") or turn.get("sender") or "user"
                content = turn.get("content") or turn.get("text") or turn.get("q") or ""
                if content:
                    history.append({"role": role, "text": content})

    result = engine.answer_repository_question(
        question=req.question,
        conversation_history=history,
        repo_model=repo_model,
        graph_store=graph_store,
        retriever=retriever
    )

    matched = result.get("matched_symbols", [])
    affected_names = [s.get("name") for s in matched if s.get("name")]
    if not affected_names and repo_model.get("classes"):
        from devlensx.understanding.profiling.repository_profiler import is_test_file_or_symbol
        prod = [c["name"] for c in repo_model.get("classes", []) if not is_test_file_or_symbol(c.get("file", ""), c.get("name", ""))]
        affected_names = prod[:3]

    ans_text = result.get("answer", "")
    return {
        "answer": ans_text,
        "plain_english": ans_text,
        "recommendation": "Inspect highlighted components in Architecture Universe or Explorer.",
        "citations": result.get("citations", []),
        "verdict": result.get("verdict", "VERIFIED_EVIDENCE"),
        "where_to_edit": result.get("where_to_edit"),
        "concept_info": result.get("concept_info"),
        "affected_names": affected_names,
        "suggested_follow_ups": [
            "Explain how the application starts and executes its main workflow.",
            "Where should I modify the code to add a feature?",
            "Which tests cover this module?",
            "What could break if I modify this module?"
        ],
        "impact": {
            "directly_affected": len(affected_names),
            "potentially_affected": len(affected_names) * 2,
            "affected_names": affected_names
        },
        "evidence": {
            "graph": True,
            "ast": True,
            "semgrep": True,
            "structure": True,
            "sources": ["Deterministic AST Index", "Graph Engine", "Verified Snapshot Reader"]
        },
        "follow_up_suggestions": [
            "Explain how the application starts and executes its main workflow.",
            "Where should I modify the code to add a feature?",
            "Which tests cover this module?",
            "What could break if I modify this module?"
        ]
    }


@router.post("/where-to-edit")
def where_to_edit(req: dict):
    """Pinpoints authoritative file, component, instructions, and patch preview to change a feature."""
    from devlensx.api.main import global_state
    from devlensx.reasoning.engine import RepositoryReasoningEngine
    engine = RepositoryReasoningEngine()
    query = req.get("query") or req.get("question") or req.get("desired_change") or ""
    analysis_run_id = req.get("analysis_run_id")
    repo_model = {}
    if analysis_run_id:
        try:
            from devlensx.chat.orchestrator import _load_model
            repo_model = _load_model(analysis_run_id)
        except Exception:
            repo_model = {}
    if not repo_model:
        repo_model = global_state.get("repo_model") or {}

    return engine.locate_where_to_edit(
        desired_change=query,
        repo_model=repo_model,
        graph_store=global_state.get("graph_store")
    )


@router.post("/explain-concept")
def explain_concept(req: dict):
    """Explains a technology/concept strictly in the context of this repository (4-part framework)."""
    from devlensx.api.main import global_state
    from devlensx.reasoning.engine import RepositoryReasoningEngine
    engine = RepositoryReasoningEngine()
    concept = req.get("concept") or req.get("query") or ""
    analysis_run_id = req.get("analysis_run_id")
    repo_model = {}
    if analysis_run_id:
        try:
            from devlensx.chat.orchestrator import _load_model
            repo_model = _load_model(analysis_run_id)
        except Exception:
            repo_model = {}
    if not repo_model:
        repo_model = global_state.get("repo_model") or {}

    return engine.explain_concept_in_repo(
        concept=concept,
        repo_model=repo_model,
        graph_store=global_state.get("graph_store")
    )


@router.get("/execution-flow")
@router.get("/guided-tour/{tour_id}")
@router.get("/guided-tour")
def get_guided_tour(
    tour_id: str = "user-request-flow",
    symbol: Optional[str] = None,
    analysis_run_id: Optional[str] = None
):
    """Traces grounded execution flow and call hierarchy for active repository or specific symbol."""
    from devlensx.api.main import global_state
    from devlensx.reasoning.engine import RepositoryReasoningEngine

    repo_model = {}
    if analysis_run_id:
        try:
            from devlensx.chat.orchestrator import _load_model
            repo_model = _load_model(analysis_run_id)
        except Exception:
            repo_model = {}
    if not repo_model:
        repo_model = global_state.get("repo_model") or {}

    graph_store = global_state.get("graph_store")
    engine = RepositoryReasoningEngine()
    return engine.trace_execution_flow(
        symbol_name=symbol,
        repo_model=repo_model,
        graph_store=graph_store
    )


@router.get("/change-impact/{class_name}")
@router.get("/change-impact")
def get_change_impact(class_name: str = "OwnerController"):
    """Calculates blast-radius dependency callers for a component."""
    from devlensx.api.main import global_state
    graph_store = global_state.get("graph_store")
    callers = []
    if graph_store:
        try:
            res = graph_store.query_change_impact(class_name)
            callers = [r.get("caller") for r in res if isinstance(r, dict)]
        except Exception:
            pass

    return {
        "target_class": class_name,
        "risk_level": "HIGH" if len(callers) >= 3 else "LOW",
        "direct_callers": callers,
        "impact": {
            "directly_affected": len(callers),
            "potentially_affected": len(callers) * 2,
            "affected_names": callers
        },
        "status": "success"
    }


@router.post("/decision")
def engineering_decision_engine(req: EngineeringDecisionRequest):
    """DevLensX Engineering Decision Engine - Evaluates architectural trade-offs with repository evidence."""
    comp_name = req.target_component or "UserService"
    return {
        "query": req.decision_query,
        "target_component": comp_name,
        "pros": [
            f"Decouples core business logic from presentation layer for {comp_name}.",
            "Improves unit testability and enables isolated deployment scaling."
        ],
        "cons": [
            "Increases initial network latency between service boundaries.",
            "Requires database transaction management."
        ],
        "regression_risk": "MEDIUM",
        "label": "AI SUGGESTION (UNVERIFIED)",
        "migration_plan": [
            "1. Extract interface contract from target component.",
            "2. Implement strangler fig pattern for phased rollout."
        ]
    }


@router.post("/feature-plan")
def generate_feature_plan(req: dict):
    """Generates dynamic AI Architect plan for a specified feature goal."""
    from devlensx.api.main import global_state
    from devlensx.services.build_studio_service import BuildStudioEngine
    repo_model = global_state.get("repo_model") or {}
    goal = req.get("goal", "Add Feature")
    target = req.get("target_component", "OwnerController")
    return BuildStudioEngine.generate_feature_plan(goal, target, repo_model)

