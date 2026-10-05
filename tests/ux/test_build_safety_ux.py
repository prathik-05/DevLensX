import tempfile, hashlib
from pathlib import Path
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence.resolver import register_snapshot
from devlensx.chat.orchestrator import store_model

def test_build_safety_message():
    content = Path("web/src/components/DocsPage.tsx").read_text(encoding="utf-8")
    assert "No files have been modified" in content or "Change Plan Generated" in content
    assert "AI_SUGGESTION" in content

def test_build_no_autowrite_api():
    tmp = tempfile.mkdtemp()
    repo = Path(tmp) / "r"
    repo.mkdir()
    (repo / "A.java").write_text("public class A {}", encoding="utf-8")
    before = hashlib.sha256((repo / "A.java").read_bytes()).hexdigest()
    register_snapshot("build_ux", "run_build_ux", str(repo), "h1")
    store_model("run_build_ux", {"repo": "build_ux", "classes": [{"name": "A", "package": "", "stereotype": "Controller", "kind": "class", "file": "A.java", "is_test": False, "methods": [], "endpoints": []}]})
    c = TestClient(app)
    r = c.post("/api/workspace/run_build_ux/build/plan", json={"task": "Add feature", "target_symbol": "A"})
    assert r.status_code == 200
    after = hashlib.sha256((repo / "A.java").read_bytes()).hexdigest()
    assert before == after
    import shutil; shutil.rmtree(tmp, ignore_errors=True)
