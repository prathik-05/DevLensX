"""
DevLensX Evidence Models (D5)

Normalized evidence representation. Every piece of evidence belongs to an
immutable repository snapshot identified by:

    repository_id + analysis_run_id + commit_hash

A citation is NEVER resolved by filename alone.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class EvidenceType(str, Enum):
    AST = "AST"
    GRAPH = "GRAPH"
    CONFIG = "CONFIG"
    GIT = "GIT"
    VECTOR = "VECTOR"


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNKNOWN_SNAPSHOT = "UNKNOWN_SNAPSHOT"     # analysis_run_id not registered
    STALE_COMMIT = "STALE_COMMIT"             # snapshot exists, commit changed
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PATH_VIOLATION = "PATH_VIOLATION"         # traversal / escape attempt
    BINARY_FILE = "BINARY_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_RANGE = "INVALID_RANGE"


@dataclass
class EvidenceRef:
    """A fully-qualified pointer into an immutable repository snapshot."""
    repository_id: str
    analysis_run_id: str
    file_path: str
    line_start: int = 1
    line_end: int = 1
    commit_hash: Optional[str] = None
    symbol_id: Optional[str] = None
    symbol_name: Optional[str] = None
    evidence_type: EvidenceType = EvidenceType.AST

    def citation_str(self) -> str:
        return f"{self.file_path}#L{self.line_start}-L{self.line_end}"

    def to_citation(self) -> str:
        return self.citation_str()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "symbol_id": self.symbol_id,
            "symbol_name": self.symbol_name,
            "evidence_type": self.evidence_type.value,
            "citation": self.citation_str(),
        }


@dataclass
class SourceLine:
    line_number: int
    content: str
    in_range: bool = False


@dataclass
class ResolvedEvidence:
    """Result of resolving an EvidenceRef against a snapshot."""
    status: ResolutionStatus
    ref: EvidenceRef
    message: str = ""
    lines: List[SourceLine] = field(default_factory=list)
    total_lines: int = 0
    file_language: Optional[str] = None

    @property
    def resolved(self) -> bool:
        return self.status == ResolutionStatus.RESOLVED

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "status": self.status.value,
            "resolved": self.resolved,
            "message": self.message,
            "ref": self.ref.to_dict(),
        }
        if self.resolved:
            payload.update({
                "lines": [
                    {"n": l.line_number, "content": l.content, "in_range": l.in_range}
                    for l in self.lines
                ],
                "total_lines": self.total_lines,
                "file_language": self.file_language,
            })
        return payload


@dataclass
class SnapshotRecord:
    """Registered repository snapshot metadata for evidence resolution."""
    repository_id: str
    analysis_run_id: str
    repo_path: str
    commit_hash: Optional[str] = None