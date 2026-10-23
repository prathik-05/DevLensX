"""
Tests for Scanner API Routes (P6-B)
"""

from fastapi.testclient import TestClient
from devlensx.api.main import app

client = TestClient(app)


def test_get_scanners_status():
    response = client.get("/api/scanners")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "plugins" in data
    assert "ast-grep" in data["plugins"]
    assert "repomix" in data["plugins"]
    assert data["plugins"]["ast-grep"]["installed"] is True
    assert data["plugins"]["repomix"]["installed"] is True


def test_toggle_scanner():
    response = client.post("/api/scanners/toggle", json={"plugin_name": "repomix", "enabled": False})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["enabled"] is False

    # Toggle back
    response2 = client.post("/api/scanners/toggle", json={"plugin_name": "repomix", "enabled": True})
    assert response2.status_code == 200
    assert response2.json()["enabled"] is True
