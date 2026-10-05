"""
DevLensX Evidence Resolver (D5)

Resolves EvidenceRefs against registered repository snapshots.

CRITICAL INVARIANT:
    A citation resolves ONLY through the full identity tuple:

        repository_id + analysis_run_id + commit_hash + file_path + range

    Resolution NEVER falls back to filename lookup. This prevents
    Repo A's OwnerController.java citation from ever displaying
    Repo B's OwnerController.java.
"""

import threading
from typing import Dict, Optional, List

from devlensx.evidence.models import (
    EvidenceRef,
    EvidenceType,
    ResolutionStatus,
    ResolvedEvidence,
    SnapshotRecord,
)
from devlensx.evidence.source_reader import SourceReader


class SnapshotRegistry:
    """Thread-safe registry of analysis snapshots keyed by analysis_run_id."""

    def __init__(self):
        self._snapshots: Dict[str, SnapshotRecord] = {}
        self._lock = threading.Lock()

    def register(
        self,
        repository_id: str,
        analysis_run_id: str,
        repo_path: str,
        commit_hash: Optional[str] = None,
    ) -> SnapshotRecord:
        record = SnapshotRecord(
            repository_id=repository_id,
            analysis_run_id=analysis_run_id,
            repo_path=str(repo_path),
            commit_hash=commit_hash,
        )
        with self._lock:
            self._snapshots[analysis_run_id] = record
        return record

    def get(self, analysis_run_id: str) -> Optional[SnapshotRecord]:
        with self._lock:
            snap = self._snapshots.get(analysis_run_id)
            if snap is not None:
                return snap

        # Recovery from validated persistent snapshot storage (fail-closed, no cross-run fallback)
        try:
            from devlensx.core.persistence import get_storage_manager
            recovered = get_storage_manager().load_snapshot(analysis_run_id)
            if recovered is not None:
                snap_rec, model = recovered
                with self._lock:
                    self._snapshots[analysis_run_id] = snap_rec
                # Restore exact model into orchestrator store
                try:
                    from devlensx.chat.orchestrator import _model_store
                    _model_store[analysis_run_id] = model
                except Exception:
                    pass
                return snap_rec
        except Exception:
            pass
        return None

    def remove(self, analysis_run_id: str) -> bool:
        with self._lock:
            return self._snapshots.pop(analysis_run_id, None) is not None

    def list_for_repository(self, repository_id: str) -> List[SnapshotRecord]:
        with self._lock:
            in_memory = [
                s for s in self._snapshots.values()
                if s.repository_id == repository_id
            ]
        # Include persisted snapshots if any
        try:
            from devlensx.core.persistence import get_storage_manager
            stored = get_storage_manager().list_snapshots(repository_id)
            seen = {s.analysis_run_id for s in in_memory}
            for m in stored:
                rid = m.get("analysis_run_id")
                if rid and rid not in seen:
                    in_memory.append(SnapshotRecord(
                        repository_id=m["repository_id"],
                        analysis_run_id=rid,
                        repo_path=m.get("repo_path", ""),
                        commit_hash=m.get("commit_hash"),
                    ))
        except Exception:
            pass
        return in_memory


# Module-level shared registry (per-process, mirrors brain_registry pattern)
_registry = SnapshotRegistry()

# Citation refs captured at analysis time, keyed by analysis_run_id.
_refs: Dict[str, List[EvidenceRef]] = {}


def get_snapshot_registry() -> SnapshotRegistry:
    return _registry


def store_snapshot_refs(analysis_run_id: str, refs: List[EvidenceRef]) -> int:
    """Persists the citation set generated during an analysis run."""
    _refs[analysis_run_id] = list(refs)
    return len(refs)


def get_snapshot_refs(analysis_run_id: str) -> Optional[List[EvidenceRef]]:
    return _refs.get(analysis_run_id)


def register_snapshot(
    repository_id: str,
    analysis_run_id: str,
    repo_path: str,
    commit_hash: Optional[str] = None,
) -> SnapshotRecord:
    """Registers an immutable snapshot for evidence resolution."""
    return _registry.register(repository_id, analysis_run_id, repo_path, commit_hash)


class EvidenceResolver:
    """Validates evidence identity, then reads source via SourceReader."""

    def __init__(self, registry: Optional[SnapshotRegistry] = None):
        self.registry = registry or _registry

    # ------------------------------------------------------------------
    @staticmethod
    def ref_from_brain_symbol(
        snapshot: SnapshotRecord,
        cls: Dict,
        evidence_type: EvidenceType = EvidenceType.AST,
        line_end_default_span: int = 10,
    ) -> EvidenceRef:
        """Builds a fully-qualified EvidenceRef from a parsed class dict."""
        try:
            end = int(cls.get("line_end") or 0)
        except (TypeError, ValueError):
            end = 0
        start_raw = cls.get("line_start") or 1
        try:
            start = int(start_raw)
        except (TypeError, ValueError):
            start = 1
        if end < start:
            end = start + line_end_default_span
        return EvidenceRef(
            repository_id=snapshot.repository_id,
            analysis_run_id=snapshot.analysis_run_id,
            commit_hash=snapshot.commit_hash,
            file_path=(cls.get("file") or "").replace("\\", "/"),
            line_start=start,
            line_end=end,
            symbol_name=cls.get("name"),
            evidence_type=evidence_type,
        )

    # ------------------------------------------------------------------
    def resolve(self, ref: EvidenceRef) -> ResolvedEvidence:
        """Resolves a reference through strict snapshot identity checks."""
        snapshot = self.registry.get(ref.analysis_run_id)

        if snapshot is None:
            return ResolvedEvidence(
                status=ResolutionStatus.UNKNOWN_SNAPSHOT,
                ref=ref,
                message=(
                    f"Unknown analysis snapshot '{ref.analysis_run_id}'. "
                    f"The repository must be analyzed before its evidence can resolve."
                ),
            )

        # Identity binding: the ref must claim the same repository as the snapshot
        if ref.repository_id and ref.repository_id != snapshot.repository_id:
            return ResolvedEvidence(
                status=ResolutionStatus.PATH_VIOLATION,
                ref=ref,
                message=(
                    f"Evidence repository '{ref.repository_id}' does not match "
                    f"snapshot repository '{snapshot.repository_id}'. "
                    f"Cross-repository citation blocked."
                ),
            )

        # Staleness check: if both hashes known and differ -> stale
        if (
            ref.commit_hash
            and snapshot.commit_hash
            and ref.commit_hash != snapshot.commit_hash
        ):
            return ResolvedEvidence(
                status=ResolutionStatus.STALE_COMMIT,
                ref=ref,
                message=(
                    f"Citation was generated at commit {ref.commit_hash} but the "
                    f"indexed snapshot is at {snapshot.commit_hash}. Re-analyze to refresh."
                ),
            )

        reader = SourceReader(snapshot.repo_path)
        result = reader.read_range(ref, context_lines=0)
        # Bind resolved evidence back to the authoritative snapshot identity
        if result.resolved:
            result.ref.commit_hash = result.ref.commit_hash or snapshot.commit_hash
        return result


# Shared resolver instance
_resolver = EvidenceResolver()


def get_evidence_resolver() -> EvidenceResolver:
    return _resolver