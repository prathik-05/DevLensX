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
        }