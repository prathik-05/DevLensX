"""Workspace context — canonical for all D9 operations."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from devlensx.evidence.models import EvidenceRef


@dataclass
class WorkspaceContext:
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str] = None

    page_id: Optional[str] = None
    section_id: Optional[str] = None
    symbol_id: Optional[str] = None
    diagram_id: Optional[str] = None

    selected_files: List[str] = field(default_factory=list)
    selected_evidence: List[EvidenceRef] = field(default_factory=list)

    current_task: Optional[str] = None
    mode: Optional[str] = None  # BUILD | DEBUG | REVIEW | IMPACT | CHAT

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "page_id": self.page_id,
            "section_id": self.section_id,
            "symbol_id": self.symbol_id,
            "diagram_id": self.diagram_id,
            "selected_files": self.selected_files,
            "selected_evidence": [r.to_dict() for r in self.selected_evidence],
            "current_task": self.current_task,
            "mode": self.mode,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkspaceContext":
        ev = []
        for r in d.get("selected_evidence", []):
            try:
                ev.append(EvidenceRef(**{k: r[k] for k in ["repository_id","analysis_run_id","file_path","line_start","line_end"] if k in r}))
            except Exception:
                pass
        return cls(
            repository_id=d["repository_id"],
            analysis_run_id=d["analysis_run_id"],
            commit_hash=d.get("commit_hash"),
            page_id=d.get("page_id"),
            section_id=d.get("section_id"),
            symbol_id=d.get("symbol_id"),
            diagram_id=d.get("diagram_id"),
            selected_files=list(d.get("selected_files", [])),
            selected_evidence=ev,
            current_task=d.get("current_task"),
            mode=d.get("mode"),
            metadata=dict(d.get("metadata", {})),
        )