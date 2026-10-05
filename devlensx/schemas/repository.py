"""
Repository and Analysis Pydantic Schemas
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class RepositoryCreate(BaseModel):
    name: str
    path: str
    language: Optional[str] = "Java"


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    path: str
    language: str
    status: str
    created_at: datetime
    updated_at: datetime


class AnalyzeRequest(BaseModel):
    repo_path: Optional[str] = ""
    source: Optional[str] = ""
    inject_hallucination: Optional[bool] = False

    def get_target_path(self) -> str:
        return (self.repo_path or self.source or "eval_repos/sample-repo").strip()


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    category: str
    severity: str
    title: str
    claim: str
    file: Optional[str] = None
    class_name: Optional[str] = None
    critic_verdict: str = "VERIFIED"
    evidence_coverage_score: float = 100.0


class ScoreResponse(BaseModel):
    overall: float
    sub_scores: Dict[str, float]
    sub_score_explanations: Optional[Dict[str, str]] = None
