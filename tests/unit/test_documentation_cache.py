"""
DevLensX Unit Test Suite: D7.13 Documentation Cache & Stale Invalidation
Verifies that DocumentationCache retrieves snapshot-bound pages and strictly invalidates on commit change.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.documentation.cache import DocumentationCache
from devlensx.documentation.models import DocumentationPage, PageStatus


def test_documentation_cache():
    print("Executing Unit Test: D7.13 Documentation Cache...")

    cache = DocumentationCache()
    page1 = DocumentationPage(
        id="overview",
        title="Overview",
        purpose="Project purpose",
        repository_id="repo-a",
        analysis_run_id="run_001",
        commit_hash="commit_v1",
    )

    cache.store_pages("repo-a", "run_001", "commit_v1", [page1])

    # 1. Exact Hit
    p = cache.get_page("repo-a", "run_001", "commit_v1", "overview")
    assert p is not None
    assert p.id == "overview"

    # 2. Stale Commit Miss
    p_stale = cache.get_page("repo-a", "run_001", "commit_v2_new", "overview")
    assert p_stale is None

    # 3. Cache Invalidation
    cache.invalidate("repo-a")
    p_after = cache.get_page("repo-a", "run_001", "commit_v1", "overview")
    assert p_after is None

    print("  🟢 Documentation Cache Verified: Stale commits strictly invalidated.")
    print("Unit Test Documentation Cache Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_cache()
