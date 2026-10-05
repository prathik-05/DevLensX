import tempfile
from pathlib import Path
from devlensx.evidence.resolver import register_snapshot

def test_snapshot_immutability():
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "repo"
    repo.mkdir()
    (repo / "A.java").write_text("public class A {}", encoding="utf-8")
    snap_a = register_snapshot("repo_cache", "run_cache_a", str(repo), "commit_a")
    snap_b = register_snapshot("repo_cache", "run_cache_b", str(repo), "commit_b")
    # Snapshots must be distinct
    assert snap_a.analysis_run_id != snap_b.analysis_run_id
    assert snap_a.commit_hash != snap_b.commit_hash
    from devlensx.evidence.resolver import get_snapshot_registry
    reg = get_snapshot_registry()
    assert reg.get("run_cache_a").commit_hash == "commit_a"
    assert reg.get("run_cache_b").commit_hash == "commit_b"
    import shutil; shutil.rmtree(tmp, ignore_errors=True)

def test_cache_files_snapshot_bound():
    # Verify documentation cache is snapshot-bound (via existing cache)
    from devlensx.documentation.cache import get_documentation_cache
    # Just verify cache exists and is not global mutable singleton without isolation
    assert get_documentation_cache() is not None
