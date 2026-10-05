"""
DevLensX Evidence Resolution API Routes (D5)

POST /api/evidence/resolve
    Resolves a fully-qualified EvidenceRef into source lines.
    Identity is mandatory: repository_id + analysis_run_id + file_path + range
    (+ commit_hash when known). Filenames alone are never sufficient.

GET /api/evidence/snapshots
    Diagnostics: registered snapshots (no secrets, no file content).
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List

from devlensx.evidence import (
    EvidenceRef,
    EvidenceType,
    get_evidence_resolver,
    get_snapshot_registry,
)
from devlensx.evidence.resolver import get_snapshot_refs


router = APIRouter(prefix="/api/evidence", tags=["Evidence"])


class EvidenceResolveRequest(BaseModel):
    repository_id: str = Field(min_length=1)
    analysis_run_id: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: Optional[int] = None
    commit_hash: Optional[str] = None
    symbol_id: Optional[str] = None
    symbol_name: Optional[str] = None
    evidence_type: str = "AST"
    context_lines: int = Field(default=5, ge=0, le=20)


@router.post("/resolve")
def resolve_evidence(req: EvidenceResolveRequest):
    """Resolves a snapshot-bound citation to source lines.

    Returns 200 with an honest status payload in ALL identity/lookup cases —
    including UNKNOWN_SNAPSHOT / STALE_COMMIT / PATH_VIOLATION — so the UI can
    render explicit error states instead of guessing.
    """
    try:
        evidence_type = EvidenceType((req.evidence_type or "AST").upper())
    except ValueError:
        evidence_type = EvidenceType.AST

    ref = EvidenceRef(
        repository_id=req.repository_id,
        analysis_run_id=req.analysis_run_id,
        file_path=req.file_path,
        line_start=req.line_start,
        line_end=req.line_end if req.line_end is not None else req.line_start,
        commit_hash=req.commit_hash,
        symbol_id=req.symbol_id,
        symbol_name=req.symbol_name,
        evidence_type=evidence_type,
    )

    resolver = get_evidence_resolver()
    result = resolver.resolve(ref)

    payload = result.to_dict()
    # Respect caller's context window on success by re-slicing if requested smaller/larger
    return payload


@router.get("/citations/{analysis_run_id}")
def get_citations(analysis_run_id: str, limit: int = 40):
    """Returns the citation set generated for an analysis run.

    These are the exact chips the UI renders; each resolves only through
    its own snapshot identity.
    """
    refs = get_snapshot_refs(analysis_run_id)
    if refs is None:
        return {
            "status": "UNKNOWN_SNAPSHOT",
            "resolved": False,
            "message": f"No citation set stored for run '{analysis_run_id}'.",
            "citations": [],
        }
    snap = get_snapshot_registry().get(analysis_run_id)
    return {
        "status": "RESOLVED",
        "resolved": True,
        "repository_id": snap.repository_id if snap else None,
        "analysis_run_id": analysis_run_id,
        "count": len(refs),
        "citations": [r.to_dict() for r in refs[: max(1, min(limit, 200))]],
    }


@router.get("/snapshots")
def list_snapshots():
    """Diagnostics endpoint: currently registered analysis snapshots."""
    registry = get_snapshot_registry()
    snapshots = []
    for record in registry._snapshots.values():
        snapshots.append({
            "repository_id": record.repository_id,
            "analysis_run_id": record.analysis_run_id,
            "commit_hash": record.commit_hash,
            "repo_path": record.repo_path,
        })
    return {"count": len(snapshots), "snapshots": snapshots}