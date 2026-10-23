"""
DevLensX Scanner & Plugin API Routes (P6-B)

Provides endpoints to inspect, install, and execute external scanner plugins
(ast-grep, Repomix, Semgrep) with strict candidate-finding verification tracking.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from devlensx.scanners.manager import ScannerManager

router = APIRouter(prefix="/api/scanners", tags=["Scanners & Plugins"])
manager = ScannerManager()


class PluginInstallRequest(BaseModel):
    plugin_name: str = Field(..., description="Name of plugin to install (ast-grep, repomix, semgrep)")


class PluginToggleRequest(BaseModel):
    plugin_name: str
    enabled: bool


class ScanRequest(BaseModel):
    repo_path: str
    repository_id: Optional[str] = None
    analysis_run_id: Optional[str] = None
    commit_hash: Optional[str] = None


@router.get("", summary="Get status of all registered scanner plugins")
def get_scanner_status() -> Dict[str, Any]:
    """Returns installation and enablement status of all registered plugins."""
    return {
        "status": "SUCCESS",
        "plugins": manager.get_status()
    }


@router.post("/toggle", summary="Enable or disable a scanner plugin")
def toggle_scanner(req: PluginToggleRequest) -> Dict[str, Any]:
    if req.plugin_name not in manager.scanners:
        raise HTTPException(status_code=404, detail=f"Plugin '{req.plugin_name}' not found")
    manager.scanners[req.plugin_name].enabled = req.enabled
    return {
        "status": "SUCCESS",
        "plugin_name": req.plugin_name,
        "enabled": req.enabled
    }


@router.post("/install", summary="Trigger automated installation of a scanner plugin")
def install_scanner(req: PluginInstallRequest) -> Dict[str, Any]:
    res = manager.install_plugin(req.plugin_name)
    return res


@router.post("/run", summary="Run all enabled scanner plugins against a repository snapshot")
def run_scanners(req: ScanRequest) -> Dict[str, Any]:
    findings = manager.scan_all(
        repo_path=req.repo_path,
        repository_id=req.repository_id,
        analysis_run_id=req.analysis_run_id,
        commit_hash=req.commit_hash
    )
    return {
        "status": "SUCCESS",
        "repo_path": req.repo_path,
        "candidate_findings_count": len(findings),
        "candidate_findings": [f.dict() for f in findings]
    }
