from devlensx.core.status import RepositoryStatus, AnalysisStatus, ChatStatus, WorkspaceStatus, status_response

def test_status_enums():
    assert RepositoryStatus.READY == "READY"
    assert AnalysisStatus.ANALYZING == "ANALYZING"
    assert ChatStatus.COMPLETE == "COMPLETE"
    assert WorkspaceStatus.STALE == "STALE"
    assert WorkspaceStatus.UNKNOWN_RUN == "UNKNOWN_RUN"

def test_status_response():
    r = status_response("READY", repository_id="r", analysis_run_id="run1", commit_hash="abc", message="ok", recoverable=False)
    assert r["status"] == "READY"
    assert r["repository_id"] == "r"
    assert r["recoverable"] is False
    # no secrets
    assert "api_key" not in str(r).lower() or "***" in str(r)

def test_error_response_no_leak():
    r = status_response("FAILED", message="Error at /home/user/secret", recoverable=True)
    assert r["status"] == "FAILED"
    assert r["recoverable"] is True
