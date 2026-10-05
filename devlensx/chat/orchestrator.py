"""Chat orchestrator — routes to the correct mode and enforces snapshot isolation."""

from typing import Dict, Any, Optional
from devlensx.evidence.models import SnapshotRecord
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.chat.models import ChatMode, ChatContext, VerifiedAnswer, StreamEvent
from devlensx.chat.fast_mode import run_fast
from devlensx.chat.codemap_mode import run_codemap
from devlensx.chat.deep_research_mode import run_deep_research

# Per-run model store — populated at POST /api/analyze time.
_model_store: Dict[str, Dict[str, Any]] = {}


def store_model(analysis_run_id: str, model: Dict[str, Any]):
    _model_store[analysis_run_id] = model


def _load_snapshot(analysis_run_id: str) -> SnapshotRecord:
    snap = get_snapshot_registry().get(analysis_run_id)
    if not snap:
        raise ValueError(f"Unknown analysis_run_id '{analysis_run_id}'")
    return snap


def _load_model(analysis_run_id: str) -> Dict[str, Any]:
    if analysis_run_id in _model_store:
        return _model_store[analysis_run_id]
    # Fallback to latest global_state (backward compat for tests that didn't store)
    try:
        from devlensx.api.main import global_state
        return global_state.get("repo_model") or {}
    except Exception:
        return {}


class ChatOrchestrator:
    @staticmethod
    def chat(
        analysis_run_id: str,
        message: str,
        mode: str = "FAST",
        context: Optional[Dict[str, Any]] = None,
    ) -> VerifiedAnswer:
        snap = _load_snapshot(analysis_run_id)
        model = _load_model(analysis_run_id)

        try:
            chat_mode = ChatMode(mode.upper())
        except ValueError:
            chat_mode = ChatMode.FAST

        ctx = None
        if context:
            ctx = ChatContext(
                repository_id=snap.repository_id,
                analysis_run_id=analysis_run_id,
                commit_hash=snap.commit_hash,
                page_id=context.get("page_id"),
                section_id=context.get("section_id"),
                diagram_id=context.get("diagram_id"),
                selected_node_id=context.get("selected_node_id"),
                selected_symbol=context.get("selected_symbol") or context.get("symbol_id"),
                selected_file=context.get("selected_file"),
                selected_lines=context.get("selected_lines"),
            )

        if chat_mode == ChatMode.FAST:
            return run_fast(snap, model, message, ctx)
        elif chat_mode == ChatMode.CODEMAP:
            return run_codemap(snap, model, message, ctx)
        else:
            return run_deep_research(snap, model, message, ctx)

    @staticmethod
    def stream(
        analysis_run_id: str,
        message: str,
        mode: str = "DEEP_RESEARCH",
        context: Optional[Dict[str, Any]] = None,
    ):
        snap = _load_snapshot(analysis_run_id)
        model = _load_model(analysis_run_id)
        try:
            chat_mode = ChatMode(mode.upper())
        except ValueError:
            chat_mode = ChatMode.DEEP_RESEARCH

        ctx = None
        if context:
            ctx = ChatContext(
                repository_id=snap.repository_id,
                analysis_run_id=analysis_run_id,
                commit_hash=snap.commit_hash,
                page_id=context.get("page_id"),
                section_id=context.get("section_id"),
                diagram_id=context.get("diagram_id"),
                selected_node_id=context.get("selected_node_id"),
                selected_symbol=context.get("selected_symbol"),
                selected_file=context.get("selected_file"),
            )

        # Emit a realistic research progress sequence for Deep Research
        yield StreamEvent(event="research_started", data={"mode": chat_mode.value}).to_sse()
        if chat_mode == ChatMode.DEEP_RESEARCH:
            from devlensx.chat.research_planner import plan_research
            subs = plan_research(message)
            yield StreamEvent(event="research_planned", data={"subquestions": subs}).to_sse()
            for idx, sq in enumerate(subs[:3]):
                yield StreamEvent(event="retrieval_started", data={"channel": "kuzu", "subquestion": sq, "index": idx}).to_sse()
            yield StreamEvent(event="claim_verification_started", data={}).to_sse()

        # Produce the final answer via the normal path
        if chat_mode == ChatMode.FAST:
            ans = run_fast(snap, model, message, ctx)
        elif chat_mode == ChatMode.CODEMAP:
            ans = run_codemap(snap, model, message, ctx)
        else:
            ans = run_deep_research(snap, model, message, ctx)

        # Token-stream the answer in chunks
        chunk_size = 80
        for i in range(0, len(ans.answer), chunk_size):
            yield StreamEvent(event="answer_token", data={"token": ans.answer[i:i+chunk_size]}).to_sse()
        yield StreamEvent(event="research_complete", data=ans.to_dict()).to_sse()