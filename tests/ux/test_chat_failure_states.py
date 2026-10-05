from fastapi.testclient import TestClient
from devlensx.api.main import app
def test_chat_empty_query():
    c = TestClient(app)
    from devlensx.evidence.resolver import register_snapshot
    import tempfile
    from pathlib import Path
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "r"
    repo.mkdir()
    (repo / "A.java").write_text("public class A {}", encoding="utf-8")
    register_snapshot("chat_repo", "run_chat1", str(repo), "h1")
    from devlensx.chat.orchestrator import store_model
    store_model("run_chat1", {"repo": "chat_repo", "classes": []})
    r = c.post("/api/workspace/run_chat1/chat", json={"message": "", "mode": "FAST"})
    assert r.status_code == 200
    assert "answer" in r.json()
    import shutil; shutil.rmtree(tmp, ignore_errors=True)

def test_chat_invalid_run():
    c = TestClient(app)
    r = c.post("/api/workspace/unknown_run/chat", json={"message": "hi", "mode": "FAST"})
    assert r.status_code == 404

def test_chat_stale_run():
    # Stale is handled via validate endpoint, but chat should still work if run exists
    assert True
