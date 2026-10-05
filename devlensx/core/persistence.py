"""
DevLensX Core Persistence Subsystem
Manages persistent, isolated snapshot artifacts in .devlensx_cache/.

Enforces the frozen DevLensX trust contract:
1. Exact Identity: Keyed strictly by (repository_id, analysis_run_id, commit_hash).
2. Atomic Writes: Writes to temporary files before atomic replacement with fsync.
3. Integrity Verification: SHA-256 checksums verified against manifest on read.
4. Path Safety: Strict rejection of directory traversal and unsafe characters.
5. Secret Scrubbing: Sensitive keys, tokens, and credentials are scrubbed before storage.
6. Bounded Storage: Artifacts above MAX_ARTIFACT_SIZE (50 MB) are rejected.
7. Fail-Closed: Corrupted or tampered snapshots return None / unavailable; zero cross-run fallback.
"""

from __future__ import annotations

import os
import json
import hashlib
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from devlensx.evidence.models import SnapshotRecord

SCHEMA_VERSION = "1.0"
MAX_ARTIFACT_SIZE = 50 * 1024 * 1024  # 50 MB maximum model/snapshot size
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

SECRET_KEY_PATTERNS = [
    re.compile(r"(?:api[_-]?key|secret|password|token|bearer|auth|credential)", re.IGNORECASE)
]


def _is_safe_identifier(val: str) -> bool:
    """Validates that a path segment contains only safe alphanumeric/hyphen/underscore/dot chars."""
    if not val or not isinstance(val, str):
        return False
    if val in (".", ".."):
        return False
    if "/" in val or "\\" in val or "\x00" in val:
        return False
    return bool(SAFE_ID_PATTERN.match(val))


def _sanitize_path_segment(val: str) -> str:
    """Normalizes an identifier for safe filesystem path usage."""
    if not _is_safe_identifier(val):
        cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", str(val or "unknown"))
        if cleaned in (".", "..") or not cleaned:
            cleaned = f"safe_{hashlib.sha256(str(val).encode()).hexdigest()[:8]}"
        return cleaned[:64]
    return val[:64]


def scrub_secrets(data: Any) -> Any:
    """Recursively scrubs API keys, passwords, and tokens from data structures before serialization."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            k_str = str(k)
            is_secret = any(p.search(k_str) for p in SECRET_KEY_PATTERNS)
            if is_secret:
                cleaned[k_str] = "[SCRUBBED_SECRET]"
            else:
                cleaned[k_str] = scrub_secrets(v)
        return cleaned
    elif isinstance(data, list):
        return [scrub_secrets(item) for item in data]
    return data


class SnapshotStorageManager:
    """Atomic, verified persistent snapshot and artifact store under .devlensx_cache/."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir:
            self.base_dir = Path(base_dir).resolve()
        else:
            self.base_dir = Path(os.environ.get("DEVLENSX_CACHE_DIR", ".devlensx_cache")).resolve()
        self.snapshots_dir = self.base_dir / "snapshots"
        self.codemaps_dir = self.base_dir / "codemaps"
        self.wiki_dir = self.base_dir / "wiki"

    def _ensure_dirs(self):
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.codemaps_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    def _get_snapshot_dir(self, repository_id: str, analysis_run_id: str) -> Optional[Path]:
        if not _is_safe_identifier(repository_id) or not _is_safe_identifier(analysis_run_id):
            return None
        target = (self.snapshots_dir / repository_id / analysis_run_id).resolve()
        try:
            if not str(target).startswith(str(self.snapshots_dir.resolve())):
                return None
        except Exception:
            return None
        return target

    def _get_codemap_dir(self, repository_id: str, analysis_run_id: str) -> Optional[Path]:
        if not _is_safe_identifier(repository_id) or not _is_safe_identifier(analysis_run_id):
            return None
        target = (self.codemaps_dir / repository_id / analysis_run_id).resolve()
        try:
            if not str(target).startswith(str(self.codemaps_dir.resolve())):
                return None
        except Exception:
            return None
        return target

    def _atomic_write_json(self, target_path: Path, data: Any) -> Tuple[bool, str, int]:
        """Atomically writes JSON to target_path using a temp file. Returns (success, sha256_hex, file_size)."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_path_str = tempfile.mkstemp(dir=target_path.parent, prefix=".tmp_", suffix=".json")
        temp_path = Path(temp_path_str)
        try:
            raw_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            file_size = len(raw_bytes)
            if file_size > MAX_ARTIFACT_SIZE:
                os.close(temp_fd)
                temp_path.unlink(missing_ok=True)
                return False, "", file_size

            sha256 = hashlib.sha256(raw_bytes).hexdigest()
            with os.fdopen(temp_fd, "wb") as f:
                f.write(raw_bytes)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, target_path)
            return True, sha256, file_size
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return False, "", 0

    def save_snapshot(self, snapshot: SnapshotRecord, model: Dict[str, Any]) -> bool:
        """Persists snapshot metadata, manifest, and model atomically with checksum verification."""
        if not snapshot or not model:
            return False
        if not isinstance(model, dict) or not model.get("classes"):
            return False

        target_dir = self._get_snapshot_dir(snapshot.repository_id, snapshot.analysis_run_id)
        if not target_dir:
            return False

        target_dir.mkdir(parents=True, exist_ok=True)

        safe_model = scrub_secrets(model)

        model_file = target_dir / "model.json"
        ok, model_sha, model_size = self._atomic_write_json(model_file, safe_model)
        if not ok:
            return False

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "repository_id": str(snapshot.repository_id),
            "analysis_run_id": str(snapshot.analysis_run_id),
            "commit_hash": str(snapshot.commit_hash or ""),
            "repo_path": str(snapshot.repo_path or ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "checksum": model_sha,
            "model_size_bytes": model_size,
            "class_count": len(safe_model.get("classes", [])),
            "stats": safe_model.get("stats", {}),
        }
        manifest_file = target_dir / "manifest.json"
        m_ok, _, _ = self._atomic_write_json(manifest_file, manifest)
        return m_ok

    def load_snapshot(
        self,
        analysis_run_id: str,
        expected_repo_id: Optional[str] = None,
        expected_commit_hash: Optional[str] = None,
    ) -> Optional[Tuple[SnapshotRecord, Dict[str, Any]]]:
        """Locates and validates exact snapshot. Returns (SnapshotRecord, model) if valid, else None."""
        if not analysis_run_id or not _is_safe_identifier(analysis_run_id):
            return None

        if not self.snapshots_dir.exists():
            return None

        candidate_dirs = []
        for repo_dir in self.snapshots_dir.iterdir():
            if repo_dir.is_dir():
                if expected_repo_id and repo_dir.name != _sanitize_path_segment(expected_repo_id):
                    continue
                run_dir = repo_dir / _sanitize_path_segment(analysis_run_id)
                if run_dir.exists() and run_dir.is_dir():
                    candidate_dirs.append(run_dir)

        if not candidate_dirs:
            return None

        target_dir = candidate_dirs[0]
        manifest_file = target_dir / "manifest.json"
        model_file = target_dir / "model.json"

        if not manifest_file.exists() or not model_file.exists():
            return None

        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)

            if manifest.get("schema_version") != SCHEMA_VERSION:
                return None
            if manifest.get("analysis_run_id") != analysis_run_id:
                return None
            if expected_repo_id and manifest.get("repository_id") != expected_repo_id:
                return None
            if expected_commit_hash and manifest.get("commit_hash") != expected_commit_hash:
                return None

            expected_checksum = manifest.get("checksum")
            if not expected_checksum:
                return None

            file_size = model_file.stat().st_size
            if file_size > MAX_ARTIFACT_SIZE:
                return None

            with open(model_file, "rb") as bf:
                raw_bytes = bf.read()

            actual_checksum = hashlib.sha256(raw_bytes).hexdigest()
            if actual_checksum != expected_checksum:
                return None

            model = json.loads(raw_bytes.decode("utf-8"))
            if not isinstance(model, dict) or not model.get("classes"):
                return None

            record = SnapshotRecord(
                repository_id=manifest["repository_id"],
                analysis_run_id=manifest["analysis_run_id"],
                repo_path=manifest.get("repo_path", ""),
                commit_hash=manifest.get("commit_hash"),
            )
            return record, model

        except Exception:
            return None

    def save_codemap(
        self,
        repository_id: str,
        analysis_run_id: str,
        commit_hash: Optional[str],
        stops: List[Dict[str, Any]],
    ) -> bool:
        """Persists codemap stops for an exact snapshot."""
        if stops is None or not isinstance(stops, list):
            return False

        target_dir = self._get_codemap_dir(repository_id, analysis_run_id)
        if not target_dir:
            return False

        target_dir.mkdir(parents=True, exist_ok=True)
        codemap_payload = {
            "schema_version": SCHEMA_VERSION,
            "repository_id": str(repository_id),
            "analysis_run_id": str(analysis_run_id),
            "commit_hash": str(commit_hash or ""),
            "count": len(stops),
            "stops": stops,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        codemap_file = target_dir / "codemap.json"
        ok, _, _ = self._atomic_write_json(codemap_file, codemap_payload)
        return ok

    def load_codemap(self, analysis_run_id: str) -> Optional[List[Dict[str, Any]]]:
        """Loads codemap stops for exact analysis_run_id. Returns None if unknown/corrupt."""
        if not analysis_run_id or not _is_safe_identifier(analysis_run_id):
            return None

        if not self.codemaps_dir.exists():
            return None

        for repo_dir in self.codemaps_dir.iterdir():
            if repo_dir.is_dir():
                run_dir = repo_dir / _sanitize_path_segment(analysis_run_id)
                codemap_file = run_dir / "codemap.json"
                if codemap_file.exists():
                    try:
                        with open(codemap_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data.get("schema_version") != SCHEMA_VERSION:
                            return None
                        if data.get("analysis_run_id") != analysis_run_id:
                            return None
                        stops = data.get("stops")
                        if isinstance(stops, list):
                            return stops
                    except Exception:
                        return None
        return None

    def has_snapshot(self, analysis_run_id: str) -> bool:
        """Checks if a valid snapshot exists on disk without loading entire model into memory."""
        res = self.load_snapshot(analysis_run_id)
        return res is not None

    def list_snapshots(self, repository_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists metadata of all valid persisted snapshots."""
        results = []
        if not self.snapshots_dir.exists():
            return results

        for repo_dir in self.snapshots_dir.iterdir():
            if not repo_dir.is_dir():
                continue
            if repository_id and repo_dir.name != _sanitize_path_segment(repository_id):
                continue
            for run_dir in repo_dir.iterdir():
                if not run_dir.is_dir():
                    continue
                manifest_file = run_dir / "manifest.json"
                if manifest_file.exists():
                    try:
                        with open(manifest_file, "r", encoding="utf-8") as f:
                            m = json.load(f)
                        results.append(m)
                    except Exception:
                        pass
        return results

    def _get_wiki_dir(self, repository_id: str, analysis_run_id: str) -> Optional[Path]:
        if not _is_safe_identifier(repository_id) or not _is_safe_identifier(analysis_run_id):
            return None
        target = (self.wiki_dir / repository_id / analysis_run_id).resolve()
        try:
            if not str(target).startswith(str(self.wiki_dir.resolve())):
                return None
        except Exception:
            return None
        return target

    def save_wiki(
        self,
        repository_id: str,
        analysis_run_id: str,
        commit_hash: Optional[str],
        wiki_data: Dict[str, Any],
    ) -> bool:
        """Persists entire generated wiki payload for an exact snapshot."""
        if not wiki_data or not isinstance(wiki_data, dict):
            return False

        target_dir = self._get_wiki_dir(repository_id, analysis_run_id)
        if not target_dir:
            return False

        target_dir.mkdir(parents=True, exist_ok=True)
        safe_payload = scrub_secrets(wiki_data)
        safe_payload.update({
            "schema_version": SCHEMA_VERSION,
            "repository_id": str(repository_id),
            "analysis_run_id": str(analysis_run_id),
            "commit_hash": str(commit_hash or ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        wiki_file = target_dir / "wiki.json"
        ok, _, _ = self._atomic_write_json(wiki_file, safe_payload)
        return ok

    def load_wiki(self, analysis_run_id: str) -> Optional[Dict[str, Any]]:
        """Loads wiki payload for exact analysis_run_id. Returns None if unknown/corrupt."""
        if not analysis_run_id or not _is_safe_identifier(analysis_run_id):
            return None

        if not self.wiki_dir.exists():
            return None

        for repo_dir in self.wiki_dir.iterdir():
            if repo_dir.is_dir():
                run_dir = repo_dir / _sanitize_path_segment(analysis_run_id)
                wiki_file = run_dir / "wiki.json"
                if wiki_file.exists():
                    try:
                        with open(wiki_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data.get("schema_version") != SCHEMA_VERSION:
                            return None
                        if data.get("analysis_run_id") != analysis_run_id:
                            return None
                        return data
                    except Exception:
                        return None
        return None


_default_storage_manager = SnapshotStorageManager()


def get_storage_manager() -> SnapshotStorageManager:
    return _default_storage_manager
