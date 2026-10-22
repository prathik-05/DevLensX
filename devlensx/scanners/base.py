"""
DevLensX External Scanner Base Module (P6-B Scanner Adapters)

Defines the normalized interface, explicit execution statuses, and candidate finding
contract for external static analyzers (Semgrep, ast-grep).

HARD INVARIANT:
  No external tool can directly set VERIFIED.
  Scanners produce candidate claims with explicit execution status bound to
  (repository_id, analysis_run_id, commit_hash). All candidate findings must
  pass through the ClaimVerifier.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ScannerStatus(str, Enum):
    EXECUTED_MATCH = "EXECUTED_MATCH"
    EXECUTED_NO_MATCH = "EXECUTED_NO_MATCH"
    NOT_INSTALLED = "NOT_INSTALLED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class CandidateFinding(BaseModel):
    """Normalized candidate finding from an external scanner or adapter."""
    finding_id: str
    tool: str  # semgrep, ast-grep, graphify, repomix
    check_id: str
    file: str
    line: Optional[int] = None
    line_range: Optional[str] = None
    message: str
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    category: str = "Static Analysis"
    status: ScannerStatus
    repository_id: Optional[str] = None
    analysis_run_id: Optional[str] = None
    commit_hash: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

    def to_critic_finding(self) -> Dict[str, Any]:
        """Converts to a candidate finding consumable by ClaimVerifier/CriticAgent."""
        return {
            "finding_id": self.finding_id,
            "title": f"[{self.tool.upper()}] {self.check_id}",
            "agent": f"{self.tool.title()}Scanner",
            "category": self.category,
            "class_name": "",
            "file": self.file,
            "severity": self.severity,
            "claim": self.message,
            "evidence": {
                "tool": self.tool,
                "check_id": self.check_id,
                "line": self.line,
                "semgrep_confirmed": (self.tool == "semgrep" and self.status == ScannerStatus.EXECUTED_MATCH),
                "scanner_status": self.status.value,
            },
            "snapshot": {
                "repository_id": self.repository_id,
                "analysis_run_id": self.analysis_run_id,
                "commit_hash": self.commit_hash,
            }
        }


class BaseScanner:
    """Abstract base class for external scanner adapters."""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    def is_installed(self) -> bool:
        raise NotImplementedError

    def scan(
        self,
        repo_path: str,
        repository_id: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        commit_hash: Optional[str] = None
    ) -> List[CandidateFinding]:
        raise NotImplementedError
