"""
DevLensX Canonical Diagram Evidence Models (D6)

Defines structured diagram representations where every node and edge
holds full EvidenceRef provenance (repository_id + analysis_run_id + commit_hash + file_path + range).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime

from devlensx.evidence.models import EvidenceRef, EvidenceType


class DiagramType(str, Enum):
    DEPENDENCY = "DEPENDENCY"
    ARCHITECTURE = "ARCHITECTURE"
    COMPONENT = "COMPONENT"
    CALL_GRAPH = "CALL_GRAPH"
    DATA_FLOW = "DATA_FLOW"
    SEQUENCE = "SEQUENCE"


class DiagramVerdict(str, Enum):
    VERIFIED = "VERIFIED"
    AI_SUGGESTION = "AI_SUGGESTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class DiagramNode:
    """A visual graph node strictly bound to source evidence."""
    id: str
    label: str
    kind: str  # "Controller", "Service", "Repository", "Package", "Module", "Endpoint", etc.
    verdict: str = "VERIFIED"  # "VERIFIED" | "AI_SUGGESTION" | "INSUFFICIENT_EVIDENCE"
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """D6.0 Hard Invariant: VERIFIED node MUST have non-empty evidence_refs."""
        if self.verdict == "VERIFIED" and not self.evidence_refs:
            self.verdict = "INSUFFICIENT_EVIDENCE"
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "verdict": self.verdict,
            "evidence_refs": [r.to_dict() for r in self.evidence_refs],
            "metadata": self.metadata,
        }


@dataclass
class DiagramEdge:
    """A visual graph edge linking two nodes with relationship provenance."""
    source: str
    target: str
    relationship: str  # "DEPENDS_ON", "CALLS", "ROUTES_TO", "CONTAINS", etc.
    verdict: str = "VERIFIED"  # "VERIFIED" | "AI_SUGGESTION" | "INSUFFICIENT_EVIDENCE"
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """D6.0 Hard Invariant: VERIFIED edge MUST have non-empty evidence_refs."""
        if self.verdict == "VERIFIED" and not self.evidence_refs:
            self.verdict = "INSUFFICIENT_EVIDENCE"
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relationship": self.relationship,
            "verdict": self.verdict,
            "evidence_refs": [r.to_dict() for r in self.evidence_refs],
            "metadata": self.metadata,
        }


@dataclass
class DiagramValidationResult:
    valid: bool
    total_nodes: int
    verified_nodes: int
    inferred_nodes: int
    unresolved_node_evidence: int
    total_edges: int
    verified_edges: int
    inferred_edges: int
    unresolved_edge_evidence: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "total_nodes": self.total_nodes,
            "verified_nodes": self.verified_nodes,
            "inferred_nodes": self.inferred_nodes,
            "unresolved_node_evidence": self.unresolved_node_evidence,
            "total_edges": self.total_edges,
            "verified_edges": self.verified_edges,
            "inferred_edges": self.inferred_edges,
            "unresolved_edge_evidence": self.unresolved_edge_evidence,
        }


@dataclass
class Diagram:
    """A complete evidence-grounded diagram for an immutable analysis snapshot."""
    id: str
    type: DiagramType
    title: str
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str] = None
    nodes: List[DiagramNode] = field(default_factory=list)
    edges: List[DiagramEdge] = field(default_factory=list)
    mermaid_source: str = ""
    description: str = ""
    verdict: str = "VERIFIED"
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def validate_invariants(self) -> DiagramValidationResult:
        """Enforces D6.0 Hard Invariant: All VERIFIED entities must possess valid evidence_refs."""
        unresolved_node = 0
        verified_nodes = 0
        inferred_nodes = 0

        for n in self.nodes:
            if n.verdict == "VERIFIED":
                if not n.evidence_refs:
                    n.verdict = "INSUFFICIENT_EVIDENCE"
                    unresolved_node += 1
                else:
                    verified_nodes += 1
            else:
                inferred_nodes += 1

        unresolved_edge = 0
        verified_edges = 0
        inferred_edges = 0

        for e in self.edges:
            if e.verdict == "VERIFIED":
                if not e.evidence_refs:
                    e.verdict = "INSUFFICIENT_EVIDENCE"
                    unresolved_edge += 1
                else:
                    verified_edges += 1
            else:
                inferred_edges += 1

        is_valid = (unresolved_node == 0 and unresolved_edge == 0)
        return DiagramValidationResult(
            valid=is_valid,
            total_nodes=len(self.nodes),
            verified_nodes=verified_nodes,
            inferred_nodes=inferred_nodes,
            unresolved_node_evidence=unresolved_node,
            total_edges=len(self.edges),
            verified_edges=verified_edges,
            inferred_edges=inferred_edges,
            unresolved_edge_evidence=unresolved_edge,
        )

    def to_dict(self) -> Dict[str, Any]:
        validation = self.validate_invariants()
        return {
            "id": self.id,
            "type": self.type.value if hasattr(self.type, 'value') else str(self.type),
            "title": self.title,
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "generated_at": self.generated_at,
            "verdict": self.verdict,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "validation": validation.to_dict(),
            "mermaid_source": self.mermaid_source,
        }
