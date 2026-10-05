from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from enum import Enum

class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AI_SUGGESTION = "AI_SUGGESTION"
    NOT_VERIFIED = "NOT_VERIFIED"


@dataclass
class EvaluationImpact:
    """Ultimate-pipeline enrichment: structured blast-radius + risk for a case."""
    symbol: str = ""
    affected_symbols: List[str] = field(default_factory=list)
    affected_tests: List[str] = field(default_factory=list)
    affected_controllers: List[str] = field(default_factory=list)
    directly_affected: int = 0
    potentially_affected: int = 0
    risk_level: str = "LOW"
    issue_type: str = "MAINTAINABILITY"
    mermaid: str = ""
    risk_basis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol, "affected_symbols": self.affected_symbols,
            "affected_tests": self.affected_tests, "affected_controllers": self.affected_controllers,
            "directly_affected": self.directly_affected, "potentially_affected": self.potentially_affected,
            "risk_level": self.risk_level, "issue_type": self.issue_type,
            "mermaid": self.mermaid, "risk_basis": self.risk_basis,
        }


@dataclass
class ExpectedClaim:
    subject: str
    predicate: str
    object: str

    def to_dict(self): return asdict(self)

@dataclass
class ExpectedEvidence:
    file: str  # suffix match, e.g. OwnerController.java
    symbol: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None

    def to_dict(self): return asdict(self)

@dataclass
class GoldenCase:
    id: str
    repository: str
    question: str
    commit_hash: Optional[str] = None
    mode: str = "FAST"
    expected_verdict: Verdict = Verdict.VERIFIED
    expected_claim: Optional[ExpectedClaim] = None
    expected_evidence: Optional[ExpectedEvidence] = None
    # Ultimate-pipeline enrichment: structured impact + blast radius for a case
    expected_impact: Optional[EvaluationImpact] = None
    expected_blast_radius: Optional[List[str]] = None
    description: Optional[str] = None
    repository_path: Optional[str] = None  # e.g. eval_repos/spring-petclinic

    def to_dict(self):
        d = asdict(self)
        d["expected_verdict"] = self.expected_verdict.value if isinstance(self.expected_verdict, Verdict) else self.expected_verdict
        if self.expected_claim: d["expected_claim"] = self.expected_claim.to_dict()
        if self.expected_evidence: d["expected_evidence"] = self.expected_evidence.to_dict()
        if self.expected_impact:
            d["expected_impact"] = self.expected_impact.to_dict()  # type: ignore[union-attr]
        elif self.expected_blast_radius:
            # Back-compat naming (older datasets stored flat list)
            d["expected_impact"] = {"affected_symbols": list(self.expected_blast_radius or [])}
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        exp_claim = None
        if data.get("expected_claim"):
            exp_claim = ExpectedClaim(**data["expected_claim"])
        exp_ev = None
        if data.get("expected_evidence"):
            exp_ev = ExpectedEvidence(**data["expected_evidence"])
        impact = None
        if data.get("expected_impact"):
            raw = data["expected_impact"]
            if isinstance(raw, dict):
                impact = EvaluationImpact(**{k: v for k, v in raw.items()  # type: ignore[misc]
                                            if k in EvaluationImpact.__dataclass_fields__})
        elif data.get("expected_blast_radius") and isinstance(data.get("expected_blast_radius"), list):
            impact = EvaluationImpact(affected_symbols=list(data["expected_blast_radius"]))
        return GoldenCase(
            id=data["id"],
            repository=data["repository"],
            commit_hash=data.get("commit_hash"),
            question=data["question"],
            mode=data.get("mode","FAST"),
            expected_verdict=Verdict(data.get("expected_verdict", "VERIFIED")),
            expected_claim=exp_claim,
            expected_evidence=exp_ev,
            expected_impact=impact,
            expected_blast_radius=(impact.affected_symbols if impact else None),
            description=data.get("description"),
            repository_path=data.get("repository_path")
        )
