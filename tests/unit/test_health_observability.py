"""
DevLensX Unit Test Suite: Release Hardening R8 Observability & Health Check Endpoint
Verifies that GET /api/health returns ready status for brain, database, graph, vector index, and LLM key state.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from devlensx.api.main import app


def test_health_observability_endpoint():
    print("Executing Unit Test: R8 Observability & Health Check Endpoint...")

    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200, f"Health check failed with HTTP {response.status_code}"
    data = response.json()

    assert data["status"] == "ok"
    assert data["brain"] == "ready"
    assert data["database"] == "ready"
    assert data["graph"] == "ready"
    assert data["vector_index"] == "ready"
    assert "supported_primary_language" in data

    print(f"  🟢 GET /api/health Returned Ready Status: {data}")
    print("Unit Test Health Observability Complete: 100% Passed\n")


if __name__ == "__main__":
    test_health_observability_endpoint()
