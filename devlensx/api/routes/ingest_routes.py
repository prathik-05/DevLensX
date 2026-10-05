"""
DevLensX Native Repo Ingest API Routes.
Provides POST /api/ingest, GET /api/ingest/{id}/digest, and POST /api/analyze/from-ingest.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from devlensx.ingest import (
    IngestRequest,
    IngestResult,
    check_rate_limit,
    get_cached_ingest,
    ingest_repository,
)
from devlensx.pipeline import Pipeline

router = APIRouter(prefix="/api/ingest", tags=["Repo Ingest (GitIngest-style)"])
analyze_router = APIRouter(tags=["Repo Ingest (GitIngest-style)"])


class AnalyzeFromIngestRequest(BaseModel):
    ingest_id: Optional[str] = None
    url: Optional[str] = None
    branch: Optional[str] = None


@router.post("", response_model=IngestResult)
async def ingest_repo(req: IngestRequest, request: Request, full: bool = False):
    """
    Ingest a GitHub repository or local directory into a prompt-ready digest.
    Host is strictly validated to github.com for SSRF protection.
    By default returns file metadata without full content; pass ?full=true to include file contents.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip)

    return await ingest_repository(
        url_or_path=req.url,
        branch=req.branch,
        include_patterns=req.include_patterns,
        exclude_patterns=req.exclude_patterns,
        max_file_size=req.max_file_size,
        token=req.token,
        full=full,
        persist_cloned_dir=True,
    )


@router.get("/{ingest_id}/digest")
def download_digest(ingest_id: str):
    """
    Download the plain text digest formatted for LLMs.
    """
    entry = get_cached_ingest(ingest_id)
    if not entry or not entry.get("result"):
        raise HTTPException(status_code=404, detail="Ingest digest not found or expired.")

    result: IngestResult = entry["result"]
    repo_name = result.summary.repo_name or "repo"
    filename = f"{repo_name}-digest.txt"

    return Response(
        content=result.digest,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.post("/analyze/from-ingest")
async def analyze_from_ingest(req: AnalyzeFromIngestRequest, request: Request):
    """
    Feed an ingested repository directly into DevLensX analysis pipeline without cloning twice.
    """
    target_path: Optional[str] = None

    if req.ingest_id:
        entry = get_cached_ingest(req.ingest_id)
        if entry and entry.get("cloned_path") and os.path.exists(entry["cloned_path"]):
            target_path = entry["cloned_path"]

    if not target_path and req.url:
        # Run ingest to get and cache cloned path
        client_ip = request.client.host if request.client else "127.0.0.1"
        check_rate_limit(client_ip)
        result = await ingest_repository(
            url_or_path=req.url,
            branch=req.branch,
            persist_cloned_dir=True,
        )
        entry = get_cached_ingest(result.id)
        if entry and entry.get("cloned_path"):
            target_path = entry["cloned_path"]

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(
            status_code=400,
            detail="Repository not found in ingest cache. Please ingest the repository first.",
        )

    # Feed straight into DevLensX Pipeline without double cloning
    analysis_result = Pipeline.analyze(repo_path=target_path)
    return {
        "status": "success",
        "message": "Repository successfully analyzed from ingest cache.",
        "analysis": analysis_result,
        "repo_path": target_path,
    }


@analyze_router.post("/api/analyze/from-ingest")
async def analyze_from_ingest_path(req: AnalyzeFromIngestRequest, request: Request):
    return await analyze_from_ingest(req, request)

