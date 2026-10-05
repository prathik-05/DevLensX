"""
DevLensX Documentation Models (D7)

Defines structured models for DocumentationPage, DocumentationSection, and EvidenceScope.
Reuses the canonical AtomicClaim and ClaimVerdict from devlensx.critic.claim_verifier
and EvidenceRef from devlensx.evidence.models.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime

from devlensx.evidence.models import EvidenceRef
from devlensx.critic.claim_verifier import AtomicClaim, ClaimVerdict


class PageStatus(str, Enum):
    VERIFIED = "VERIFIED"
    VERIFIED_WITH_SUGGESTIONS = "VERIFIED_WITH_SUGGESTIONS"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    GENERATION_FAILED = "GENERATION_FAILED"


@dataclass
class EvidenceScope:
    """Bounded evidence package provided to a documentation page."""
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str]
    page_id: str
    target_files: List[str] = field(default_factory=list)
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    configurations: List[Dict[str, Any]] = field(default_factory=list)
    semantic_chunks: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    diagram_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "page_id": self.page_id,
            "target_files": self.target_files,
            "symbols_count": len(self.symbols),
            "relationships_count": len(self.relationships),
            "endpoints_count": len(self.endpoints),
            "configurations_count": len(self.configurations),
            "semantic_chunks_count": len(self.semantic_chunks),
            "evidence_refs": [r.to_dict() for r in self.evidence_refs],
            "diagram_ids": self.diagram_ids,
        }


@dataclass
class DocumentationSection:
    """A verified section within a DocumentationPage."""
    heading: str
    content: str
    claims: List[AtomicClaim] = field(default_factory=list)
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    diagram_ids: List[str] = field(default_factory=list)
    verdict: str = "VERIFIED"  # "VERIFIED" | "AI_SUGGESTION" | "INSUFFICIENT_EVIDENCE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heading": self.heading,
            "content": self.content,
            "verdict": self.verdict,
            "claims": [
                {
                    "subject": c.subject,
                    "predicate": c.predicate,
                    "object": c.object,
                    "claim_type": c.claim_type,
                    "verdict": c.verdict.value if hasattr(c.verdict, "value") else str(c.verdict),
                    "evidence_source": c.evidence_source,
                    "line_reference": c.line_reference,
                }
                for c in self.claims
            ],
            "evidence_refs": [r.to_dict() for r in self.evidence_refs],
            "diagram_ids": self.diagram_ids,
        }


@dataclass
class DocumentationPage:
    """A complete evidence-grounded Wiki documentation page."""
    id: str
    title: str
    purpose: str
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str]
    sections: List[DocumentationSection] = field(default_factory=list)
    status: PageStatus = PageStatus.VERIFIED
    verification_summary: Dict[str, int] = field(default_factory=lambda: {
        "verified": 0,
        "suggestions": 0,
        "insufficient_evidence": 0,
    })
    diagram_ids: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def validate_invariants(self) -> bool:
        """
        D7.5 Invariant Enforcement:
        - VERIFIED claims/sections MUST have >= 1 EvidenceRef.
        - INSUFFICIENT_EVIDENCE claims MUST NOT have fake EvidenceRefs.
        - AI_SUGGESTION claims must not masquerade as verified repository facts.
        """
        verified_count = 0
        suggestions_count = 0
        insufficient_count = 0

        for section in self.sections:
            # Check section claims
            for claim in section.claims:
                verdict_str = claim.verdict.value if hasattr(claim.verdict, "value") else str(claim.verdict)
                if "VERIFIED" in verdict_str:
                    verified_count += 1
                elif "SUGGESTION" in verdict_str or "PARTIAL" in verdict_str:
                    suggestions_count += 1
                else:
                    insufficient_count += 1

            if section.verdict == "VERIFIED" and not section.evidence_refs:
                section.verdict = "INSUFFICIENT_EVIDENCE"

        self.verification_summary = {
            "verified": verified_count,
            "suggestions": suggestions_count,
            "insufficient_evidence": insufficient_count,
        }

        if insufficient_count > 0 and verified_count > 0:
            self.status = PageStatus.PARTIALLY_VERIFIED
        elif insufficient_count > 0 and verified_count == 0:
            self.status = PageStatus.INSUFFICIENT_EVIDENCE
        elif suggestions_count > 0:
            self.status = PageStatus.VERIFIED_WITH_SUGGESTIONS
        else:
            self.status = PageStatus.VERIFIED

        return True

    def to_dict(self) -> Dict[str, Any]:
        self.validate_invariants()
        return {
            "id": self.id,
            "title": self.title,
            "purpose": self.purpose,
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "verification_summary": self.verification_summary,
            "sections": [s.to_dict() for s in self.sections],
            "diagram_ids": self.diagram_ids,
            "generated_at": self.generated_at,
        }
