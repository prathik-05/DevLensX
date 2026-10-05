from devlensx.incremental.diff import GitDiffDetector
from devlensx.incremental.models import ChangeType

def test_detect_from_list():
    changes = GitDiffDetector.detect_changed_files_from_list(["a.java", "b.java"], ChangeType.MODIFIED)
    assert len(changes) == 2
    assert changes[0].change_type == ChangeType.MODIFIED

def test_malicious_path_filtered():
    # Simulate security: detector filters .. paths
    # We test via is_safe_path indirectly - the detector drops ".."
    from pathlib import Path
    import tempfile
    tmp = tempfile.mkdtemp()
    p = Path(tmp)
    (p / "a.java").write_text("x")
    # Use git diff detector with override list containing malicious
    changes = GitDiffDetector.detect_changed_files_from_list(["../evil.java"], ChangeType.MODIFIED)
    # This helper doesn't filter, but API layer does. Test API filter:
    from fastapi.testclient import TestClient
    from devlensx.api.main import app
    from devlensx.evidence.resolver import register_snapshot
    register_snapshot("repo_diff", "run_diff1", tmp, "h1")
    c = TestClient(app)
    resp = c.post("/api/analyze/run_diff1/incremental", json={"changed_files": ["../evil.java"]})
    assert resp.status_code == 400

def test_added_modified_deleted():
    for ct in [ChangeType.ADDED, ChangeType.MODIFIED, ChangeType.DELETED, ChangeType.RENAMED]:
        fc = GitDiffDetector.detect_changed_files_from_list(["Foo.java"], ct)
        assert fc[0].change_type == ct
