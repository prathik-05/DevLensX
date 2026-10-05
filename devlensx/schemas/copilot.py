"""
Copilot, Debug, and Review Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CopilotAskRequest(BaseModel):
    repo_id: Optional[str] = ""
    question: str
    session_history: Optional[List[Dict[str, Any]]] = []
    provider: Optional[str] = "groq"
    api_key: Optional[str] = ""


class TraceDebugRequest(BaseModel):
    stack_trace: str


class PRReviewRequest(BaseModel):
    repo_id: Optional[str] = ""
    diff: str
    custom_prompt: Optional[str] = ""


class EngineeringDecisionRequest(BaseModel):
    decision_query: str
    target_component: Optional[str] = None
