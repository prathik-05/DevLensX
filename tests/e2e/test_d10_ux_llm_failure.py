from fastapi.testclient import TestClient
from devlensx.api.main import app
def test_d10_llm_failure():
    c = TestClient(app)
    r = c.get("/api/health")
    assert "llm" in r.json()
    # Chat should still work without LLM key
    import tempfile, pathlib
    from devlensx.evidence.resolver import register_snapshot
    from devlensx.chat.orchestrator import store_model
    import tempfile
    from pathlib import Path
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "r"
    repo.mkdir()
    (repo / "A.java").write_text("public class A {}", encoding="utf-8")
    register_snapshot("llm_fail", "run_llm_fail", str(repo), "h1")
    store_model("run_llm_fail", {"repo": "llm_fail", "classes": []})
    r2 = c.post("/api/workspace/run_llm_fail/chat", json={"message": "hi", "mode": "FAST"})
    assert r2.status_code == 200
    import shutil; shutil.rmtree(tmp, ignore_errors=True)
