from fastapi.testclient import TestClient
from devlensx.api.main import app
def test_health():
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "brain" in data
    assert "OPENAI_API_KEY" not in r.text
    assert "observability" in data or "brain" in data

def test_metrics_endpoint():
    c = TestClient(app)
    r = c.get("/api/observability/metrics")
    assert r.status_code == 200
    assert "metrics" in r.json()
