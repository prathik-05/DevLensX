import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence.resolver import register_snapshot

def test_workspace_context_preserved():
    c = TestClient(app)
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "r"
    repo.mkdir()
    (repo / "A.java").write_text("public class A {}", encoding="utf-8")
    register_snapshot("ws_repo", "run_ws1", str(repo), "h1")
    # Create session and set context
    r = c.post("/api/workspace/run_ws1/context", json={"active_symbol": "A"})
    assert r.status_code == 200
    assert r.json()["valid"] is True
    # Check context
    r2 = c.get("/api/workspace/run_ws1/context")
    assert r2.status_code == 200
    import shutil; shutil.rmtree(tmp, ignore_errors=True)

def test_workspace_mode_indicators():
    assert Path("web/src/components/StatusIndicator.tsx").exists()
    content = Path("web/src/components/EmptyState.tsx").read_text(encoding="utf-8")
    assert "Workspace is stale" in content

def test_build_review_boundaries():
    assert Path("web/src/components/DocsPage.tsx").read_text(encoding="utf-8").count("AI_SUGGESTION") > 0
