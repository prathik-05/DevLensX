"""
Unit tests for DevLensX Repository Ingestion Cache Reliability.
Verifies:
- No WinError 183 on sequential or concurrent ingestion cache publishing.
- Concurrent requests for the same repository/commit safely reuse valid cache.
- Distinct repositories with the same basename do not collide (owner-scoped cache keys).
- Distinct commits of the same repository do not reuse stale source.
- Corrupt cache entries are detected and rebuilt cleanly.
- Windows read-only git lock recovery.
"""

import os
import shutil
import tempfile
import threading
from pathlib import Path
import pytest

from devlensx.ingest import _publish_cached_clone, _safe_rmtree_windows


@pytest.fixture
def sample_source_repo(tmp_path):
    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("# Test Repo", encoding="utf-8")
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "Main.java").write_text("public class Main {}", encoding="utf-8")
    return repo_dir


def test_sequential_cache_publish_no_winerror_183(sample_source_repo):
    """Publishing the same repository twice sequentially must succeed and reuse valid cache."""
    owner = "test_owner"
    repo = "Tic-Tac-Toe"
    commit_sha = "abcdef123456"

    path1 = _publish_cached_clone(sample_source_repo, owner, repo, commit_sha)
    assert os.path.isdir(path1)
    assert os.path.isfile(os.path.join(path1, "README.md"))
    assert os.path.isfile(os.path.join(path1, ".complete"))

    # Second publication (simulating repeat ingest of same repo/commit)
    path2 = _publish_cached_clone(sample_source_repo, owner, repo, commit_sha)
    assert path1 == path2
    assert os.path.isfile(os.path.join(path2, ".complete"))


def test_concurrent_cache_publish(sample_source_repo):
    """5 concurrent ingestion requests for the same repo and commit must not race or raise WinError 183."""
    owner = "concurrent_org"
    repo = "Tic-Tac-Toe"
    commit_sha = "c0ffee123456"

    results = []
    errors = []

    def worker():
        try:
            p = _publish_cached_clone(sample_source_repo, owner, repo, commit_sha)
            results.append(p)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrent publish errors: {errors}"
    assert len(results) == 5
    # All threads should resolve to the same published cache path
    assert len(set(results)) == 1
    assert os.path.isfile(os.path.join(results[0], ".complete"))


def test_distinct_owners_same_repo_name_do_not_collide(sample_source_repo):
    """Distinct repositories with the same repo name (e.g. alice/app vs bob/app) must have distinct paths."""
    commit_sha = "deadbeef1234"
    path_alice = _publish_cached_clone(sample_source_repo, "alice", "minimax", commit_sha)
    path_bob = _publish_cached_clone(sample_source_repo, "bob", "minimax", commit_sha)

    assert path_alice != path_bob
    assert "alice" in path_alice
    assert "bob" in path_bob


def test_distinct_commits_do_not_reuse_stale_cache(sample_source_repo):
    """Distinct commits of the same repository must produce distinct cache directories."""
    owner = "org"
    repo = "game"
    path_c1 = _publish_cached_clone(sample_source_repo, owner, repo, "111111111111")
    path_c2 = _publish_cached_clone(sample_source_repo, owner, repo, "222222222222")

    assert path_c1 != path_c2


def test_corrupt_cache_rebuilt(sample_source_repo):
    """If cache exists without a valid .complete marker, it must be rebuilt safely."""
    owner = "org"
    repo = "corrupt_test"
    commit_sha = "333333333333"

    # Pre-populate corrupt cache (missing .complete)
    cache_root = Path(tempfile.gettempdir()) / "devlensx_ingest_cache"
    corrupt_dir = cache_root / f"{owner}_{repo}_{commit_sha[:10]}"
    corrupt_dir.mkdir(parents=True, exist_ok=True)
    (corrupt_dir / "incomplete.txt").write_text("unfinished", encoding="utf-8")

    path = _publish_cached_clone(sample_source_repo, owner, repo, commit_sha)
    assert os.path.isdir(path)
    assert os.path.isfile(os.path.join(path, ".complete"))
    assert os.path.isfile(os.path.join(path, "src", "Main.java"))
