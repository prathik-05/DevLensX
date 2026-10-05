from fastapi.testclient import TestClient
from devlensx.api.main import app
def test_request_correlation():
    c = TestClient(app)
    r = c.post("/api/analyze", json={"repo_path": "eval_repos/battleship-python"}, headers={"X-Request-ID": "req-test123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "req-test123"
    # Without header, should generate one
    r2 = c.get("/api/health")
    assert "X-Request-ID" in r2.headers
