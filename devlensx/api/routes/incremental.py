from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/analyze", tags=["Incremental"])

class IncrementalRequest(BaseModel):
    target_commit: Optional[str] = None
    changed_files: Optional[List[str]] = None  # For testing without git

@router.post("/{analysis_run_id}/incremental")
def incremental_analyze(analysis_run_id: str, req: IncrementalRequest):
    from devlensx.incremental.analyzer import IncrementalAnalyzer
    from devlensx.evidence.resolver import get_snapshot_registry
    snap = get_snapshot_registry().get(analysis_run_id)
    if not snap:
        raise HTTPException(status_code=404, detail=f"UNKNOWN_RUN:{analysis_run_id}")
    # Security: validate target_commit is hex-like, not command injection
    if req.target_commit and len(req.target_commit) > 64:
        raise HTTPException(status_code=400, detail="target_commit too long")
    if req.target_commit and any(c in req.target_commit for c in [";", "&", "|", "`", "$", "\n", " "]):
        raise HTTPException(status_code=400, detail="Invalid target_commit")
    # Validate changed_files paths
    if req.changed_files:
        for p in req.changed_files:
            if ".." in p or p.startswith("/") or (len(p) >=2 and p[1]==":"):
                raise HTTPException(status_code=400, detail=f"Invalid path: {p}")
            if "\x00" in p:
                raise HTTPException(status_code=400, detail="Invalid path")
    try:
        result = IncrementalAnalyzer.analyze(analysis_run_id, target_commit=req.target_commit, changed_files_override=req.changed_files)
        return result.to_dict()
    except ValueError as e:
        if "UNKNOWN_RUN" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Incremental analysis failed: {str(e)}")
