"""Debug stacktrace parser — reuses DebugRootCauseEngine, adds snapshot binding."""

from typing import Dict, Any
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.evidence.models import EvidenceRef, EvidenceType

class StackTraceParser:
    @staticmethod
    def parse(stack_trace: str, analysis_run_id: str) -> Dict[str, Any]:
        snap = get_snapshot_registry().get(analysis_run_id)
        if not snap:
            raise ValueError(f"UNKNOWN_RUN:{analysis_run_id}")
        from devlensx.api.main import global_state
        model = {}
        try:
            from devlensx.chat.orchestrator import _model_store
            if analysis_run_id in _model_store:
                model = _model_store[analysis_run_id]
            else:
                model = global_state.get("repo_model") or {}
        except Exception:
            pass
        from devlensx.services.debug_service import DebugRootCauseEngine
        result = DebugRootCauseEngine.analyze_stack_trace(stack_trace, model)
        # Bind snapshot identity and ensure verified locations have EvidenceRefs
        result["repository_id"] = snap.repository_id
        result["analysis_run_id"] = snap.analysis_run_id
        result["commit_hash"] = snap.commit_hash
        # Convert verified_locations to EvidenceRefs
        refs = []
        for loc in result.get("verified_locations", []):
            refs.append(EvidenceRef(
                repository_id=snap.repository_id,
                analysis_run_id=snap.analysis_run_id,
                commit_hash=snap.commit_hash,
                file_path=loc.get("file",""),
                line_start=int(loc.get("line",1)),
                line_end=int(loc.get("line",1)),
                symbol_name=loc.get("class_name"),
                evidence_type=EvidenceType.AST,
            ).to_dict())
        result["evidence_refs"] = refs
        return result