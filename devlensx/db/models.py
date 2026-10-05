"""
DevLensX Relational Database Models & Entities
"""

from typing import Optional
from datetime import datetime


class User:
    def __init__(self, id: int, email: str, hashed_password: str, full_name: Optional[str] = "Developer"):
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.created_at = datetime.utcnow()


class Repository:
    def __init__(self, id: int, owner_id: int, name: str, path: str, language: str = "Java", status: str = "pending"):
        self.id = id
        self.owner_id = owner_id
        self.name = name
        self.path = path
        self.language = language
        self.status = status
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class AnalysisRun:
    def __init__(self, id: int, repository_id: int, status: str = "running", overall_score: float = 0.0):
        self.id = id
        self.repository_id = repository_id
        self.status = status
        self.started_at = datetime.utcnow()
        self.completed_at = None
        self.parser_version = "1.0.0-javalang"
        self.error_message = None
        self.overall_score = overall_score


class Finding:
    def __init__(self, id: int, analysis_run_id: int, category: str, severity: str, title: str, claim: str, file: Optional[str] = None):
        self.id = id
        self.analysis_run_id = analysis_run_id
        self.category = category
        self.severity = severity
        self.title = title
        self.claim = claim
        self.file = file
        self.critic_verdict = "VERIFIED"
        self.evidence_coverage_score = 100.0
        self.created_at = datetime.utcnow()
