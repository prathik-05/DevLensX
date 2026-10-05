"""
DevLensX Chat Models (D8)

Shared data contracts for all three chat modes.
Reuses EvidenceRef and AtomicClaim from canonical subsystems.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class ChatMode(str, Enum):
    FAST = "FAST"
    CODEMAP = "CODEMAP"
    DEEP_RESEARCH = "DEEP_RESEARCH"


class ChatIntent(str, Enum):
    OVERVIEW = "OVERVIEW"
    ARCHITECTURE = "ARCHITECTURE"
    DATA_FLOW = "DATA_FLOW"
    CHANGE_IMPACT = "CHANGE_IMPACT"
    DEBUG = "DEBUG"
    SECURITY = "SECURITY"
    EXPLANATION = "EXPLANATION"
    CODEMAP_REQUEST = "CODEMAP_REQUEST"
    RESEARCH = "RESEARCH"


@dataclass
class ChatContext:
    """Hierarchical UI context — priority P1 (highest) to P6 (lowest)."""
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str] = None
    # P4 / P3 / P2 / P1
    page_id: Optional[str] = None
    section_id: Optional[str] = None
    diagram_id: Optional[str] = None
    selected_node_id: Optional[str] = None
    selected_edge_id: Optional[str] = None
    selected_symbol: Optional[str] = None
    selected_file: Optional[str] = None
    selected_lines: Optional[str] = None  # e.g. "23-45"

    def priority_summary(self) -> List[str]:
        ordered: List[str] = []
        if self.selected_file or self.selected_symbol:
            ordered.append(f"source:{self.selected_file or self.selected_symbol}")
        if self.selected_node_id:
            ordered.append(f"node:{self.selected_node_id}")
        if self.section_id:
            ordered.append(f"section:{self.section_id}")
        if self.page_id:
            ordered.append(f"page:{self.page_id}")
        ordered.append(f"repo:{self.repository_id}")
        return ordered

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "page_id": self.page_id,
            "section_id": self.section_id,
            "diagram_id": self.diagram_id,
            "selected_node_id": self.selected_node_id,
            "selected_edge_id": self.selected_edge_id,
            "selected_symbol": self.selected_symbol,
            "selected_file": self.selected_file,
            "selected_lines": self.selected_lines,
        }


@dataclass
class ChatRequest:
    message: str
    mode: ChatMode = ChatMode.FAST
    context: Optional[ChatContext] = None
    history: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ChatEvidence:
    """Consolidated evidence for an answer, split by trust level."""
    deterministic_symbols: List[Dict[str, Any]] = field(default_factory=list)
    deterministic_relationships: List[Dict[str, Any]] = field(default_factory=list)
    deterministic_source_refs: List[Dict[str, Any]] = field(default_factory=list)  # EvidenceRef dicts
    semantic_chunks: List[Dict[str, Any]] = field(default_factory=list)
    diagrams: List[Dict[str, Any]] = field(default_factory=list)
    total_symbols: int = 0
    total_relationships: int = 0

    def is_empty(self) -> bool:
        return not (self.deterministic_symbols or self.deterministic_relationships)


@dataclass
class VerifiedAnswer:
    answer: str
    mode: ChatMode
    repository_id: str = ""
    analysis_run_id: str = ""
    commit_hash: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    claims: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    diagrams: List[Dict[str, Any]] = field(default_factory=list)
    research: Optional[Dict[str, Any]] = None
    verification_summary: Dict[str, int] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "mode": self.mode.value if hasattr(self.mode, "value") else str(self.mode),
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "context": self.context,
            "claims": self.claims,
            "evidence_refs": self.evidence_refs,
            "diagrams": self.diagrams,
            "research": self.research,
            "verification_summary": self.verification_summary,
            "generated_at": self.generated_at,
        }


@dataclass
class StreamEvent:
    event: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        import json
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"