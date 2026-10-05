from fastapi.testclient import TestClient
from devlensx.api.main import app
def test_d10_failure_states():
    c = TestClient(app)
    r = c.get("/api/workspace/unknown123/context")
    assert r.status_code in (404, 422)
    assert "Traceback" not in r.text
    # ErrorBoundary
    assert __import__("pathlib").Path("web/src/components/ErrorBoundary.tsx").exists()
