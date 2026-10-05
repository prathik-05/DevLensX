"""
DevLensX Multi-Repository Workspace Federation (Phase P4-A)

Manages multi-repository workspaces while strictly preserving snapshot isolation.

CRITICAL INVARIANTS:
1. Canonical Snapshot Identity:
       (repository_id, analysis_run_id, commit_hash)
   workspace_id is session/routing context, NEVER part of the snapshot identity.

2. Isolation Guarantee:
   Repositories within a workspace NEVER share AST models, Kùzu graphs,
   vector indexes, or EvidenceRefs. No synthetic combined models.

3. Explicit Cross-Repository Queries:
   Cross-repo queries require explicit (source_repo_id, target_repo_id)
   and are marked as CROSS_REPO_FEDERATED. Implicit cross-repo bleeding is forbidden.

4. Fail-Closed:
   Missing workspace, repository, or snapshot fails closed (REPOSITORY_NOT_IN_WORKSPACE,
   SNAPSHOT_NOT_FOUND, REPOSITORY_MISMATCH).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from devlensx.evidence.models import SnapshotRecord
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.workspace.models import WorkspaceSession
from devlensx.workspace.session import get_workspace_registry


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FederatedRepoMeta:
    """Metadata for a repository registered in a federated workspace."""
    repository_id: str
    repo_name: str
    repo_path: str
    active_analysis_run_id: Optional[str] = None
    active_commit_hash: Optional[str] = None
    registered_at: str = field(default_factory=_utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "active_analysis_run_id": self.active_analysis_run_id,
            "active_commit_hash": self.active_commit_hash,
            "registered_at": self.registered_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class FederatedWorkspace:
    """A multi-repository workspace container."""
    workspace_id: str
    name: str
    repositories: Dict[str, FederatedRepoMeta] = field(default_factory=dict)
    active_repository_id: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "repositories": {k: v.to_dict() for k, v in self.repositories.items()},
            "active_repository_id": self.active_repository_id,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


class FederatedWorkspaceManager:
    """
    Thread-safe manager for federated workspaces.
    Enforces repository isolation and validates against SnapshotRegistry.
    """

    def __init__(self):
        self._workspaces: Dict[str, FederatedWorkspace] = {}
        self._lock = threading.Lock()

    def create_workspace(self, workspace_id: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> FederatedWorkspace:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("WORKSPACE_ID_REQUIRED")
        ws_id = workspace_id.strip()
        with self._lock:
            if ws_id in self._workspaces:
                return self._workspaces[ws_id]
            ws = FederatedWorkspace(
                workspace_id=ws_id,
                name=name or ws_id,
                metadata=dict(metadata or {}),
            )
            self._workspaces[ws_id] = ws
            return ws

    def get_workspace(self, workspace_id: str) -> Optional[FederatedWorkspace]:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def list_workspaces(self) -> List[FederatedWorkspace]:
        with self._lock:
            return list(self._workspaces.values())

    def delete_workspace(self, workspace_id: str) -> bool:
        with self._lock:
            return self._workspaces.pop(workspace_id, None) is not None

    def add_repository(
        self,
        workspace_id: str,
        repository_id: str,
        repo_name: Optional[str] = None,
        repo_path: Optional[str] = None,
        analysis_run_id: Optional[str] = None,
        commit_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FederatedRepoMeta:
        if not repository_id or not repository_id.strip():
            raise ValueError("REPOSITORY_ID_REQUIRED")
        clean_repo_id = repository_id.strip()

        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"WORKSPACE_NOT_FOUND:{workspace_id}")

            meta = FederatedRepoMeta(
                repository_id=clean_repo_id,
                repo_name=repo_name or clean_repo_id,
                repo_path=str(repo_path or ""),
                active_analysis_run_id=analysis_run_id,
                active_commit_hash=commit_hash,
                metadata=dict(metadata or {}),
            )
            ws.repositories[clean_repo_id] = meta
            if ws.active_repository_id is None:
                ws.active_repository_id = clean_repo_id
            return meta

    def remove_repository(self, workspace_id: str, repository_id: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"WORKSPACE_NOT_FOUND:{workspace_id}")
            removed = ws.repositories.pop(repository_id, None) is not None
            if ws.active_repository_id == repository_id:
                ws.active_repository_id = next(iter(ws.repositories.keys())) if ws.repositories else None
            return removed

    def set_active_repository(self, workspace_id: str, repository_id: str) -> bool:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"WORKSPACE_NOT_FOUND:{workspace_id}")
            if repository_id not in ws.repositories:
                raise ValueError(f"REPOSITORY_NOT_IN_WORKSPACE:{repository_id}")
            ws.active_repository_id = repository_id
            return True

    def get_active_repository(self, workspace_id: str) -> Optional[FederatedRepoMeta]:
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws or not ws.active_repository_id:
                return None
            return ws.repositories.get(ws.active_repository_id)

    def bind_snapshot(
        self,
        workspace_id: str,
        repository_id: str,
        analysis_run_id: str,
        commit_hash: Optional[str] = None,
    ) -> SnapshotRecord:
        """
        Binds an analyzed snapshot to a repository in the workspace.
        Validates snapshot against SnapshotRegistry and ensures exact repo match.
        """
        snap_reg = get_snapshot_registry()
        snap = snap_reg.get(analysis_run_id)
        if not snap:
            raise ValueError(f"SNAPSHOT_NOT_FOUND:{analysis_run_id}")
        if snap.repository_id != repository_id:
            raise ValueError(f"REPOSITORY_MISMATCH:{snap.repository_id}!={repository_id}")
        if commit_hash and snap.commit_hash and snap.commit_hash != commit_hash:
            raise ValueError(f"COMMIT_MISMATCH:{snap.commit_hash}!={commit_hash}")

        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"WORKSPACE_NOT_FOUND:{workspace_id}")
            if repository_id not in ws.repositories:
                raise ValueError(f"REPOSITORY_NOT_IN_WORKSPACE:{repository_id}")
            
            repo_meta = ws.repositories[repository_id]
            repo_meta.active_analysis_run_id = snap.analysis_run_id
            repo_meta.active_commit_hash = snap.commit_hash
            if not repo_meta.repo_path and snap.repo_path:
                repo_meta.repo_path = snap.repo_path

        # Also initialize or get WorkspaceSession for this run
        ws_reg = get_workspace_registry()
        ws_reg.create_or_get(snap.analysis_run_id)
        return snap

    def resolve_snapshot_for_repo(
        self,
        workspace_id: str,
        repository_id: str,
        analysis_run_id: Optional[str] = None,
    ) -> SnapshotRecord:
        """
        Resolves the exact snapshot for a repository within a workspace.
        Fails closed if the repo is not in the workspace or the snapshot does not exist.
        """
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if not ws:
                raise ValueError(f"WORKSPACE_NOT_FOUND:{workspace_id}")
            if repository_id not in ws.repositories:
                raise ValueError(f"REPOSITORY_NOT_IN_WORKSPACE:{repository_id}")
            repo_meta = ws.repositories[repository_id]
            target_run_id = analysis_run_id or repo_meta.active_analysis_run_id

        if not target_run_id:
            raise ValueError(f"NO_ACTIVE_SNAPSHOT:{repository_id}")

        snap = get_snapshot_registry().get(target_run_id)
        if not snap:
            raise ValueError(f"SNAPSHOT_NOT_FOUND:{target_run_id}")
        if snap.repository_id != repository_id:
            raise ValueError(f"REPOSITORY_MISMATCH:{snap.repository_id}!={repository_id}")

        return snap

    def route_cross_repo_query(
        self,
        workspace_id: str,
        source_repo_id: str,
        target_repo_id: str,
        query_type: str,
        query_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Routes an explicit cross-repository query.
        Ensures both repositories belong to the workspace and have valid snapshots.
        Results are isolated per repository and marked as CROSS_REPO_FEDERATED.
        """
        source_snap = self.resolve_snapshot_for_repo(workspace_id, source_repo_id)
        target_snap = self.resolve_snapshot_for_repo(workspace_id, target_repo_id)

        # Cross-repository boundary envelope
        return {
            "mode": "CROSS_REPO_FEDERATED",
            "workspace_id": workspace_id,
            "query_type": query_type,
            "source": {
                "repository_id": source_repo_id,
                "analysis_run_id": source_snap.analysis_run_id,
                "commit_hash": source_snap.commit_hash,
            },
            "target": {
                "repository_id": target_repo_id,
                "analysis_run_id": target_snap.analysis_run_id,
                "commit_hash": target_snap.commit_hash,
            },
            "payload": query_payload,
            "timestamp": _utc_now_iso(),
        }


# Global singleton instance
_federated_manager: Optional[FederatedWorkspaceManager] = None
_federated_lock = threading.Lock()


def get_federated_workspace_manager() -> FederatedWorkspaceManager:
    global _federated_manager
    if _federated_manager is None:
        with _federated_lock:
            if _federated_manager is None:
                _federated_manager = FederatedWorkspaceManager()
    return _federated_manager


def reset_federated_workspace_manager():
    """Testing helper to reset in-memory workspaces."""
    global _federated_manager
    with _federated_lock:
        _federated_manager = FederatedWorkspaceManager()
