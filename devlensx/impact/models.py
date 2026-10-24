from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ImpactResult:
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str]
    target_symbol: str
    direct: List[Dict[str, Any]] = field(default_factory=list)
    downstream: List[Dict[str, Any]] = field(default_factory=list)
    tests: List[Dict[str, Any]] = field(default_factory=list)
    configs: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    diagram: Optional[Dict[str, Any]] = None
    status: str = "OK"  # OK | TARGET_NOT_FOUND
    risk_level: str = "LOW"
    # Grounded intelligence & relationship distinction (Milestone 5)
    direct_callers: List[Dict[str, Any]] = field(default_factory=list)
    transitive_callers: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    potential_regressions: List[str] = field(default_factory=list)
    recommended_validations: List[str] = field(default_factory=list)
    coverage_limitations: List[str] = field(default_factory=list)
    execution_order_type: str = "VERIFIED_CALL_ORDER"  # VERIFIED_CALL_ORDER | INFERRED_ARCHITECTURE_ORDER | UNRESOLVED_RUNTIME_BEHAVIOR
    risk_assessment: Dict[str, Any] = field(default_factory=dict)
    diff_analysis: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "target_symbol": self.target_symbol,
            "direct": self.direct,
            "downstream": self.downstream,
            "tests": self.tests,
            "configs": self.configs,
            "evidence_refs": self.evidence_refs,
            "diagram": self.diagram,
            "status": self.status,
            "risk_level": self.risk_level,
            "direct_callers": self.direct_callers,
            "transitive_callers": self.transitive_callers,
            "dependencies": self.dependencies,
            "potential_regressions": self.potential_regressions,
            "recommended_validations": self.recommended_validations,
            "coverage_limitations": self.coverage_limitations,
            "execution_order_type": self.execution_order_type,
            "risk_assessment": self.risk_assessment,
            "diff_analysis": self.diff_analysis,
        }
