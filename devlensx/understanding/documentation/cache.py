"""
DevLensX Documentation Intelligence - Documentation Cache
Caches generated documentation keyed to repository identity + analysis_run_id + commit hash.
"""

import os
import json
import hashlib
import pickle
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from devlensx.understanding.documentation.planner import DocumentationTree, DocumentationCacheKey
from devlensx.understanding.documentation.page_generator import GeneratedPage


@dataclass
class CacheEntry:
    """A cached documentation entry."""
    cache_key: DocumentationCacheKey
    documentation_tree: DocumentationTree
    generated_pages: Dict[str, GeneratedPage]
    created_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentationCache:
    """Persistent cache for generated documentation."""
    
    def __init__(self, cache_dir: str = ".devlensx-runtime/doc_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self._index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """Loads cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_index(self):
        """Saves cache index to disk."""
        try:
            with open(self.index_file, "w") as f:
                json.dump(self._index, f, indent=2)
        except Exception:
            pass
    
    def _get_cache_key_str(self, cache_key: DocumentationCacheKey) -> str:
        """Generates a filesystem-safe cache key string."""
        return cache_key.to_string().replace("/", "_").replace(":", "_")
    
    def _get_cache_path(self, cache_key: DocumentationCacheKey) -> Path:
        """Gets the cache file path for a key."""
        key_str = self._get_cache_key_str(cache_key)
        return self.cache_dir / f"{key_str}.pkl"
    
    def get(self, cache_key: DocumentationCacheKey) -> Optional[CacheEntry]:
        """Retrieves cached documentation if it exists and is valid."""
        key_str = cache_key.to_string()
        
        # Check index first
        if key_str not in self._index:
            return None
        
        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            # Index is stale
            del self._index[key_str]
            self._save_index()
            return None
        
        # Verify commit hash matches (if available)
        index_entry = self._index[key_str]
        if cache_key.commit_hash and index_entry.get("commit_hash") != cache_key.commit_hash:
            return None  # Repository has changed
        
        try:
            with open(cache_path, "rb") as f:
                entry = pickle.load(f)
            return entry
        except Exception:
            # Corrupted cache
            self.invalidate(cache_key)
            return None
    
    def set(self, entry: CacheEntry):
        """Stores documentation in cache."""
        key_str = entry.cache_key.to_string()
        cache_path = self._get_cache_path(entry.cache_key)
        
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(entry, f)
            
            # Update index
            self._index[key_str] = {
                "repository_id": entry.cache_key.repository_id,
                "analysis_run_id": entry.cache_key.analysis_run_id,
                "commit_hash": entry.cache_key.commit_hash,
                "created_at": entry.created_at,
                "page_count": len(entry.generated_pages),
                "cache_file": cache_path.name,
            }
            self._save_index()
        except Exception:
            # Failed to cache
            pass
    
    def invalidate(self, cache_key: DocumentationCacheKey):
        """Invalidates a specific cache entry."""
        key_str = cache_key.to_string()
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            try:
                cache_path.unlink()
            except Exception:
                pass
        
        if key_str in self._index:
            del self._index[key_str]
            self._save_index()
    
    def invalidate_repository(self, repository_id: str):
        """Invalidates all cache entries for a repository."""
        keys_to_remove = []
        for key_str, entry in self._index.items():
            if entry.get("repository_id") == repository_id:
                cache_path = self.cache_dir / entry["cache_file"]
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                    except Exception:
                        pass
                keys_to_remove.append(key_str)
        
        for key_str in keys_to_remove:
            del self._index[key_str]
        
        self._save_index()
    
    def get_repository_cache_info(self, repository_id: str) -> Optional[Dict[str, Any]]:
        """Gets cache info for the latest analysis run of a repository."""
        matching = [
            entry for entry in self._index.values()
            if entry.get("repository_id") == repository_id
        ]
        if not matching:
            return None
        
        # Return most recent
        latest = max(matching, key=lambda e: e.get("created_at", 0))
        return latest
    
    def cleanup_old_entries(self, max_age_days: int = 30, max_entries_per_repo: int = 5):
        """Cleans up old cache entries."""
        now = datetime.now().timestamp()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        # Group by repository
        by_repo: Dict[str, list] = {}
        for key_str, entry in self._index.items():
            repo_id = entry.get("repository_id", "unknown")
            if repo_id not in by_repo:
                by_repo[repo_id] = []
            by_repo[repo_id].append((key_str, entry))
        
        # Clean each repo
        for repo_id, entries in by_repo.items():
            # Sort by creation time (newest first)
            entries.sort(key=lambda x: x[1].get("created_at", 0), reverse=True)
            
            # Keep only max_entries_per_repo
            for key_str, entry in entries[max_entries_per_repo:]:
                self.invalidate(DocumentationCacheKey(
                    repository_id=entry["repository_id"],
                    analysis_run_id=entry["analysis_run_id"],
                    commit_hash=entry.get("commit_hash"),
                ))
            
            # Remove old entries
            for key_str, entry in entries:
                created_at = entry.get("created_at", 0)
                if now - created_at > max_age_seconds:
                    self.invalidate(DocumentationCacheKey(
                        repository_id=entry["repository_id"],
                        analysis_run_id=entry["analysis_run_id"],
                        commit_hash=entry.get("commit_hash"),
                    ))


# Global cache instance
_documentation_cache: Optional[DocumentationCache] = None


def get_documentation_cache(cache_dir: Optional[str] = None) -> DocumentationCache:
    """Gets the global documentation cache instance."""
    global _documentation_cache
    if _documentation_cache is None:
        _documentation_cache = DocumentationCache(cache_dir or ".devlensx-runtime/doc_cache")
    return _documentation_cache


def get_cached_documentation(cache_key: DocumentationCacheKey) -> Optional[CacheEntry]:
    """Convenience function to get cached documentation."""
    return get_documentation_cache().get(cache_key)


def cache_documentation(entry: CacheEntry):
    """Convenience function to cache documentation."""
    get_documentation_cache().set(entry)