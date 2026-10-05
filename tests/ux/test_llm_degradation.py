from fastapi.testclient import TestClient
from devlensx.api.main import app
import tempfile
from pathlib import Path
from devlensx.evidence.resolver import register_snapshot
from devlensx.chat.orchestrator import store_model

def test_llm_unavailable_still_deterministic():
    c = TestClient(app)
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "r"
    repo.mkdir()
    (repo / "A.java").write_text("public class A {}", encoding="utf-8")
    register_snapshot("llm_repo", "run_llm1", str(repo), "h1")
    store_model("run_llm1", {"repo": "llm_repo", "classes": [{"name": "A", "package": "", "stereotype": "Controller", "kind": "class", "file": "A.java", "is_test": False, "methods": [], "endpoints": []}]})
    # Chat should work even without LLM key (fallback)
    r = c.post("/api/workspace/run_llm1/chat", json={"message": "Where is A?", "mode": "FAST"})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    import shutil; shutil.rmtree(tmp, ignore_errors=True)

def test_health_llm_flag():
    c = TestClient(app)
    r = c.get("/api/health")
    assert "llm" in r.json()
    assert r.json()["llm"] in ("available", "unavailable (deterministic features active)")
