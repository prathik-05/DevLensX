import pytest
from fastapi.testclient import TestClient
from devlensx.api.main import app

client = TestClient(app)

def test_governance_demo_seed_endpoint():
    res = client.post("/api/governance/demo/seed")
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert "rules_demo" in data
    assert "contracts_demo" in data

    # Verify evaluate works with demo snapshot
    rules_demo = data["rules_demo"]
    eval_res = client.post("/api/governance/evaluate", json={
        "analysis_run_id": rules_demo["analysis_run_id"],
        "repository_id": rules_demo["repository_id"],
    })
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["valid"] is True
    assert eval_data["total_findings"] >= 1

    # Verify contract verification works with demo contracts
    c_demo = data["contracts_demo"]
    c_res = client.post("/api/governance/contracts/verify", json=c_demo)
    assert c_res.status_code == 200
    c_data = c_res.json()
    assert c_data["valid"] is True
    assert c_data["report"]["breaking_count"] >= 1


def test_gitingest_wiki_digest_endpoint():
    res = client.post("/api/wiki/digest", json={
        "source": "devlensx/mcp",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "summary" in data
    assert "tree" in data
    assert "content" in data
    assert "prompt_digest" in data
    assert data["stats"]["files_analyzed"] == 3
    assert data["stats"]["estimated_tokens"] > 0
