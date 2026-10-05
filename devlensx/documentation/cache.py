"""
DevLensX Documentation Cache (D7.13)

Caches generated DocumentationPages strictly bound by (repository_id, analysis_run_id, commit_hash).
Detects stale commits and automatically invalidates outdated snapshots.
"""

from typing import Dict, List, Optional, Any
import threading
from devlensx.documentation.models import DocumentationPage


class DocumentationCache:
    """Thread-safe snapshot-bound cache for verified DocumentationPages."""

    def __init__(self):
        # Key: (repository_id, analysis_run_id, commit_hash) -> Dict[page_id, DocumentationPage]
        self._cache: Dict[str, Dict[str, DocumentationPage]] = {}
        self._lock = threading.Lock()

    def _make_key(self, repository_id: str, analysis_run_id: str, commit_hash: Optional[str]) -> str:
        c_hash = commit_hash or "head"
        return f"{repository_id}::{analysis_run_id}::{c_hash}"

    def store_pages(self, repository_id: str, analysis_run_id: str, commit_hash: Optional[str], pages: List[DocumentationPage]):
        key = self._make_key(repository_id, analysis_run_id, commit_hash)
        with self._lock:
            if key not in self._cache:
                self._cache[key] = {}
            for page in pages:
                self._cache[key][page.id] = page

    def get_page(self, repository_id: str, analysis_run_id: str, commit_hash: Optional[str], page_id: str) -> Optional[DocumentationPage]:
        key = self._make_key(repository_id, analysis_run_id, commit_hash)
        with self._lock:
            repo_cache = self._cache.get(key, {})
            return repo_cache.get(page_id)

    def list_pages(self, repository_id: str, analysis_run_id: str, commit_hash: Optional[str]) -> List[DocumentationPage]:
        key = self._make_key(repository_id, analysis_run_id, commit_hash)
        with self._lock:
            repo_cache = self._cache.get(key, {})
            return list(repo_cache.values())

    def invalidate(self, repository_id: str, commit_hash: Optional[str] = None):
        """Invalidates all caches for a repository, or a specific commit hash."""
        with self._lock:
            keys_to_del = []
            for k in self._cache:
                if k.startswith(f"{repository_id}::"):
                    if commit_hash is None or f"::{commit_hash}" in k:
                        keys_to_del.append(k)
            for k in keys_to_del:
                del self._cache[k]


_doc_cache = DocumentationCache()


def get_documentation_cache() -> DocumentationCache:
    return _doc_cache
