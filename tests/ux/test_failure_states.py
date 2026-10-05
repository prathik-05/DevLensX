from fastapi.testclient import TestClient
from devlensx.api.main import app
def test_unknown_snapshot_returns_structured_error():
    c = TestClient(app)
    r = c.get("/api/workspace/unknown_run_404/context")
    assert r.status_code in (404, 422)
    data = r.json()
    assert "detail" in data or "status" in data
    # should not leak stack trace
    assert "Traceback" not in r.text

def test_invalid_zip_returns_structured_error():
    c = TestClient(app)
    r = c.post("/api/upload-zip", files={"file": ("bad.zip", b"notzip", "application/zip")})
    assert r.status_code in (400, 403, 422)
    assert "Traceback" not in r.text

def test_health_has_llm_available_flag():
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    assert "llm" in r.json()
