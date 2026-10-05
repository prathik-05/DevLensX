"""
DevLensX Codemap API Route — GET /api/codemap/{analysis_id}
"""

from fastapi import APIRouter, HTTPException
from typing import Any

router = APIRouter(prefix="/api/codemap", tags=["Codemap"])

@router.get("/{analysis_id}")
def get_codemap(analysis_id: str):
    """Returns tour stops ordered by centrality/blast-radius from exact snapshot."""
    try:
        from devlensx.codemap import get_codemap_stops
        stops = get_codemap_stops(analysis_id)
        if stops is None:
            # Snapshot does not exist in memory or persistent storage -> 404
            raise HTTPException(
                status_code=404,
                detail=f"SNAPSHOT_NOT_FOUND: Analysis '{analysis_id}' not found. Run /api/analyze first."
            )
        # Valid snapshot: return stops (can be count: 0 if no tour stops)
        return {
            "analysis_id": analysis_id,
            "count": len(stops),
            "stops": stops,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Codemap build failed: {str(e)}")
