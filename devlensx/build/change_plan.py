from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class BuildStep:
    file: str
    symbol: str
    operation: str  # ADD | MODIFY
    reason: str
    source: str = "AI_SUGGESTION"
    depends_on: List[str] = field(default_factory=list)
    risk: str = "LOW"
    verification_required: bool = True
    evidence_ref: Optional[Dict[str, Any]] = None
    status: str = "AI_SUGGESTION"

    def to_dict(self)->Dict[str,Any]:
        return {
            "file": self.file, "symbol": self.symbol, "operation": self.operation,
            "reason": self.reason, "source": self.source, "depends_on": self.depends_on,
            "risk": self.risk, "verification_required": self.verification_required,
            "evidence_ref": self.evidence_ref, "status": self.status,
        }

@dataclass
class ChangePlan:
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str]
    task: str
    steps: List[BuildStep] = field(default_factory=list)
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    verification_required: bool = True
    def to_dict(self):
        return {
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "task": self.task,
            "steps": [s.to_dict() for s in self.steps],
            "evidence_refs": self.evidence_refs,
            "verification_required": self.verification_required,
        }