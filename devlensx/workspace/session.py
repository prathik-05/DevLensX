"""Thread-safe workspace session registry. References existing SnapshotRegistry."""

import threading
from typing import Dict, Optional, List
from datetime import datetime

from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.workspace.models import WorkspaceSession, WorkspaceStatus
from devlensx.workspace.events import WorkspaceEvent
from devlensx.workspace.context import WorkspaceContext


class WorkspaceSessionRegistry:
    def __init__(self):
        self._sessions: Dict[str, WorkspaceSession] = {}
        self._events: Dict[str, List[WorkspaceEvent]] = {}
        self._lock = threading.Lock()

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def create_or_get(self, analysis_run_id: str) -> WorkspaceSession:
        snap = get_snapshot_registry().get(analysis_run_id)
        if not snap:
            raise ValueError(f"UNKNOWN_RUN:{analysis_run_id}")
        with self._lock:
            if analysis_run_id in self._sessions:
                sess = self._sessions[analysis_run_id]
                sess.last_accessed = self._now()
                return sess
            sess = WorkspaceSession(
                repository_id=snap.repository_id,
                analysis_run_id=snap.analysis_run_id,
                commit_hash=snap.commit_hash,
                repo_path=snap.repo_path,
                created_at=self._now(),
                last_accessed=self._now(),
            )
            self._sessions[analysis_run_id] = sess
            self._events[analysis_run_id] = []
            return sess

    def get(self, analysis_run_id: str) -> Optional[WorkspaceSession]:
        with self._lock:
            return self._sessions.get(analysis_run_id)

    def validate(self, analysis_run_id: str, repository_id: Optional[str] = None, commit_hash: Optional[str] = None) -> tuple[bool, str]:
        snap = get_snapshot_registry().get(analysis_run_id)
        if not snap:
            return False, WorkspaceStatus.UNKNOWN_RUN
        if repository_id and snap.repository_id != repository_id:
            return False, WorkspaceStatus.REPOSITORY_MISMATCH
        # Check commit hash against snapshot (source of truth)
        if commit_hash and snap.commit_hash and commit_hash != snap.commit_hash:
            return False, WorkspaceStatus.STALE_COMMIT
        sess = self.get(analysis_run_id)
        if sess and commit_hash and sess.commit_hash and commit_hash != sess.commit_hash:
            return False, WorkspaceStatus.STALE_COMMIT
        # Stale workspace: snapshot commit drifted since session creation
        if sess and snap.commit_hash and sess.commit_hash != snap.commit_hash:
            return False, WorkspaceStatus.STALE
        return True, WorkspaceStatus.ACTIVE

    def update_context(self, analysis_run_id: str, updates: dict) -> WorkspaceSession:
        sess = self.get(analysis_run_id)
        if not sess:
            sess = self.create_or_get(analysis_run_id)
        with self._lock:
            for k in ("active_page","active_section","active_symbol","active_diagram","current_task","mode"):
                if k in updates and updates[k] is not None:
                    setattr(sess, k, updates[k])
            if "selected_files" in updates:
                sess.selected_files = list(updates["selected_files"])
            sess.last_accessed = self._now()
            return sess

    def emit_event(self, event: WorkspaceEvent):
        with self._lock:
            self._events.setdefault(event.analysis_run_id, []).append(event)

    def get_events(self, analysis_run_id: str) -> List[WorkspaceEvent]:
        with self._lock:
            return list(self._events.get(analysis_run_id, []))

    def to_context(self, sess: WorkspaceSession) -> WorkspaceContext:
        return WorkspaceContext(
            repository_id=sess.repository_id,
            analysis_run_id=sess.analysis_run_id,
            commit_hash=sess.commit_hash,
            page_id=sess.active_page,
            section_id=sess.active_section,
            symbol_id=sess.active_symbol,
            diagram_id=sess.active_diagram,
            selected_files=list(sess.selected_files),
            current_task=sess.current_task,
            mode=sess.mode,
        )


_registry = WorkspaceSessionRegistry()

def get_workspace_registry() -> WorkspaceSessionRegistry:
    return _registry