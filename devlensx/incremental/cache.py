"""Snapshot immutability helpers for incremental analysis."""
from typing import Dict, Any, Optional
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.chat.orchestrator import _model_store
from devlensx.api.main import global_state

def get_model_for_run(analysis_run_id: str) -> Dict[str, Any]:
    if analysis_run_id in _model_store:
        return _model_store[analysis_run_id]
    return global_state.get("repo_model") or {}

def get_graph_for_run(analysis_run_id: str):
    return global_state.get("graph_store")

def snapshot_exists(analysis_run_id: str) -> bool:
    return get_snapshot_registry().get(analysis_run_id) is not None
