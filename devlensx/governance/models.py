"""
DevLensX Architectural Governance & Contract Models (Phase P5)

Core domain types for architectural rules, candidate violations,
cycle classifications, and cross-service contract verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from devlensx.evidence.models import EvidenceRef, EvidenceType


class CycleType(str, Enum):
    """Explicitly distinguished architectural cycle types (P5 mandatory correction)."""
    IMPORT_CYCLE = "IMPORT_CYCLE"
    INHERITANCE_CYCLE = "INHERITANCE_CYCLE"
    CALL_GRAPH_CYCLE = "CALL_GRAPH_CYCLE"


class BreakingChangeType(str, Enum):
    """Explicitly defined breaking contract change types (P5 mandatory correction)."""
    ENDPOINT_REMOVED = "ENDPOINT_REMOVED"
    HTTP_METHOD_CHANGED = "HTTP_METHOD_CHANGED"
    REQUIRED_PARAM_ADDED = "REQUIRED_PARAM_ADDED"
    PARAM_TYPE_CHANGED = "PARAM_TYPE_CHANGED"
    RESPONSE_TYPE_CHANGED = "RESPONSE_TYPE_CHANGED"
    REQUIRED_RESPONSE_FIELD_REMOVED = "REQUIRED_RESPONSE_FIELD_REMOVED"
    RESPONSE_FIELD_TYPE_CHANGED = "RESPONSE_FIELD_TYPE_CHANGED"
    ENUM_VALUE_REMOVED = "ENUM_VALUE_REMOVED"
    STATUS_CODE_CONTRACT_CHANGED = "STATUS_CODE_CONTRACT_CHANGED"


@dataclass
class ArchitecturalRule:
    """
    Declarative architectural rule specification.
    Uses structured selectors (packages, symbols, stereotypes, annotations)
    rather than uncontrolled pattern strings.
    """
    rule_id: str
    name: str
    rule_type: str  # LAYER_HIERARCHY | FORBIDDEN_DEPENDENCY | CYCLE_DETECTION | REQUIRED_ANNOTATION
    scope: Dict[str, Any] = field(default_factory=dict)
    source_selector: Dict[str, Any] = field(default_factory=dict)
    target_selector: Optional[Dict[str, Any]] = None
    constraint: str = "FORBIDDEN"  # FORBIDDEN | MUST_USE | NO_CYCLE | REQUIRED
    severity: str = "WARNING"  # CRITICAL | WARNING | INFO
    description: str = ""
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "scope": dict(self.scope),
            "source_selector": dict(self.source_selector),
            "target_selector": dict(self.target_selector) if self.target_selector else None,
            "constraint": self.constraint,
            "severity": self.severity,
            "description": self.description,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchitecturalRule":
        return cls(
            rule_id=data["rule_id"],
            name=data["name"],
            rule_type=data["rule_type"],
            scope=data.get("scope", {}),
            source_selector=data.get("source_selector", {}),
            target_selector=data.get("target_selector"),
            constraint=data.get("constraint", "FORBIDDEN"),
            severity=data.get("severity", "WARNING"),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
        )


@dataclass
class CandidateViolation:
    """
    A raw violation candidate emitted by the Governance Evaluator.
    CRITICAL INVARIANT: The governance evaluator itself never assigns VERIFIED.
    Candidate must be passed through Evidence Resolver & ClaimVerifier.
    """
    rule_id: str
    violation_type: str
    severity: str
    source_symbol: str
    target_symbol: Optional[str]
    file_path: str
    line_start: int
    line_end: int
    evidence_ref: Optional[EvidenceRef] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "violation_type": self.violation_type,
            "severity": self.severity,
            "source_symbol": self.source_symbol,
            "target_symbol": self.target_symbol,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "evidence_ref": self.evidence_ref.to_dict() if self.evidence_ref else None,
            "description": self.description,
            "metadata": dict(self.metadata),
        }


@dataclass
class GovernanceFinding:
    """
    A verified governance finding with official verification verdict.
    Verdict is strictly assigned through ClaimVerifier / Evidence Resolver.
    """
    rule_id: str
    violation_type: str
    severity: str
    verdict: str  # VERIFIED | AI_SUGGESTION | INSUFFICIENT_EVIDENCE
    source_symbol: str
    target_symbol: Optional[str]
    file_path: str
    line_start: int
    line_end: int
    evidence_ref: Optional[Dict[str, Any]]
    description: str
    committable_fix: Optional[str] = None
    requires_user_action: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "violation_type": self.violation_type,
            "severity": self.severity,
            "verdict": self.verdict,
            "source_symbol": self.source_symbol,
            "target_symbol": self.target_symbol,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "evidence_ref": self.evidence_ref,
            "description": self.description,
            "committable_fix": self.committable_fix,
            "requires_user_action": self.requires_user_action,
        }


@dataclass
class ContractDifference:
    """A single difference between provider and consumer endpoint contracts."""
    change_type: BreakingChangeType | str
    is_breaking: bool
    endpoint_path: str
    http_method: str
    details: str
    provider_spec: Dict[str, Any] = field(default_factory=dict)
    consumer_spec: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_type": self.change_type.value if isinstance(self.change_type, Enum) else str(self.change_type),
            "is_breaking": self.is_breaking,
            "endpoint_path": self.endpoint_path,
            "http_method": self.http_method,
            "details": self.details,
            "provider_spec": dict(self.provider_spec),
            "consumer_spec": dict(self.consumer_spec),
        }
