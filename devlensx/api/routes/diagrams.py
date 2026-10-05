"""
DevLensX Diagram API Routes (D6)

GET /api/diagrams/{analysis_run_id}
    Returns metadata/catalog for all generated diagrams in an analysis run.

GET /api/diagrams/{analysis_run_id}/{diagram_type}
    Returns canonical Diagram JSON (nodes, edges, evidence_refs, mermaid_source).
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

from devlensx.diagrams.models import DiagramType
from devlensx.diagrams.generator import get_diagram_store, generate_all_diagrams
from devlensx.evidence.resolver import get_snapshot_registry


router = APIRouter(prefix="/api/diagrams", tags=["Diagrams"])


@router.get("/{analysis_run_id}")
def list_diagrams(analysis_run_id: str):
    """Lists all available evidence-grounded diagrams for an analysis run."""
    store = get_diagram_store()
    diagrams = store.list_all(analysis_run_id)

    if not diagrams:
        # Attempt on-the-fly generation if snapshot is registered
        snap = get_snapshot_registry().get(analysis_run_id)
        if snap:
            from devlensx.api.main import global_state
            model = global_state.get("repo_model") or {}
            generate_all_diagrams(snap, model)
            diagrams = store.list_all(analysis_run_id)

    if not diagrams:
        return {
            "status": "UNKNOWN_SNAPSHOT",
            "analysis_run_id": analysis_run_id,
            "count": 0,
            "diagrams": [],
        }

    return {
        "status": "RESOLVED",
        "analysis_run_id": analysis_run_id,
        "count": len(diagrams),
        "diagrams": [
            {
                "id": d["id"],
                "type": d["type"],
                "title": d["title"],
                "node_count": len(d.get("nodes", [])),
                "edge_count": len(d.get("edges", [])),
                "verdict": d.get("verdict", "VERIFIED"),
                "description": d.get("description", ""),
            }
            for d in diagrams
        ],
    }


@router.get("/{analysis_run_id}/{diagram_type}")
def get_diagram(analysis_run_id: str, diagram_type: str):
    """Returns a specific evidence-grounded diagram with all node/edge provenance."""
    store = get_diagram_store()
    diagram = store.get(analysis_run_id, diagram_type)

    if diagram is None:
        snap = get_snapshot_registry().get(analysis_run_id)
        if snap:
            from devlensx.api.main import global_state
            model = global_state.get("repo_model") or {}
            generate_all_diagrams(snap, model)
            diagram = store.get(analysis_run_id, diagram_type)

    if diagram is None:
        raise HTTPException(
            status_code=404,
            detail=f"Diagram '{diagram_type}' not found for analysis run '{analysis_run_id}'.",
        )

    return diagram.to_dict()
