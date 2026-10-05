"""Workspace events — snapshot-bound state machine."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from devlensx.workspace.context import WorkspaceContext

VALID_EVENT_TYPES = {
    "PAGE_SELECTED", "SECTION_SELECTED", "SYMBOL_SELECTED", "DIAGRAM_SELECTED",
    "IMPACT_REQUESTED", "IMPACT_COMPLETED",
    "CHAT_REQUESTED",
    "BUILD_REQUESTED", "BUILD_PLAN_CREATED",
    "DEBUG_REQUESTED", "DEBUG_TRACE_COMPLETED",
    "REVIEW_REQUESTED", "REVIEW_COMPLETED",
    "SOURCE_OPENED",
    "WORKSPACE_CREATED", "WORKSPACE_ACCESSED",
}


@dataclass
class WorkspaceEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    repository_id: str = ""
    analysis_run_id: str = ""
    commit_hash: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    event_type: str = "PAGE_SELECTED"
    context: Optional[WorkspaceContext] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "context": self.context.to_dict() if self.context else None,
            "payload": self.payload,
        }