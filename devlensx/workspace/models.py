"""Workspace models."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class WorkspaceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STALE = "WORKSPACE_STALE"
    UNKNOWN_RUN = "UNKNOWN_RUN"
    REPOSITORY_MISMATCH = "REPOSITORY_MISMATCH"
    STALE_COMMIT = "STALE_COMMIT"


@dataclass
class WorkspaceSession:
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str]
    repo_path: str
    active_page: Optional[str] = None
    active_section: Optional[str] = None
    active_symbol: Optional[str] = None
    active_diagram: Optional[str] = None
    selected_files: List[str] = field(default_factory=list)
    selected_evidence: List[Dict[str, Any]] = field(default_factory=list)
    current_task: Optional[str] = None
    mode: Optional[str] = None
    created_at: str = ""
    last_accessed: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "repo_path": self.repo_path,
            "active_page": self.active_page,
            "active_section": self.active_section,
            "active_symbol": self.active_symbol,
            "active_diagram": self.active_diagram,
            "selected_files": self.selected_files,
            "selected_evidence": self.selected_evidence,
            "current_task": self.current_task,
            "mode": self.mode,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
        }