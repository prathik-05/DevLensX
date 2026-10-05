"""Unified workspace orchestrator — validates, updates context, delegates, emits events."""

from typing import Dict, Any, Optional
from devlensx.workspace.session import get_workspace_registry
from devlensx.workspace.events import WorkspaceEvent
from devlensx.evidence.resolver import get_snapshot_registry


class UnifiedWorkspaceOrchestrator:
    @staticmethod
    def ensure_session(analysis_run_id: str) -> Dict[str, Any]:
        reg = get_workspace_registry()
        snap = get_snapshot_registry().get(analysis_run_id)
        if not snap:
            return {"status": "UNKNOWN_RUN", "valid": False}
        sess = reg.create_or_get(analysis_run_id)
        return {"status": "ACTIVE", "valid": True, "session": sess.to_dict(), "context": reg.to_context(sess).to_dict()}

    @staticmethod
    def update_context(analysis_run_id: str, updates: Dict[str, Any], event_type: str = "PAGE_SELECTED") -> Dict[str, Any]:
        reg = get_workspace_registry()
        valid, status = reg.validate(analysis_run_id)
        if not valid:
            return {"status": status, "valid": False}
        sess = reg.update_context(analysis_run_id, updates)
        ctx = reg.to_context(sess)
        ev = WorkspaceEvent(
            repository_id=sess.repository_id,
            analysis_run_id=sess.analysis_run_id,
            commit_hash=sess.commit_hash,
            event_type=event_type,
            context=ctx,
            payload=dict(updates),
        )
        reg.emit_event(ev)
        return {"status": "ACTIVE", "valid": True, "session": sess.to_dict(), "context": ctx.to_dict(), "event": ev.to_dict()}

    @staticmethod
    def validate_snapshot(analysis_run_id: str, repository_id: Optional[str] = None, commit_hash: Optional[str] = None) -> Dict[str, Any]:
        reg = get_workspace_registry()
        valid, status = reg.validate(analysis_run_id, repository_id, commit_hash)
        return {"valid": valid, "status": status}