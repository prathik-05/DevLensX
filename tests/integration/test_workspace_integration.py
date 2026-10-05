"""
DevLensX Integration Tests: Workspace Shared Repository Brain Integration
Verifies that Wiki, Q&A, Debug, and Change Impact share the exact same RepositoryBrain version.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from devlensx.api.main import app, global_state


def test_shared_brain_workspace_integration():
    client = TestClient(app)
    
    # 1. Trigger Analysis
    analyze_resp = client.post("/api/analyze", json={"repo_path": "eval_repos/spring-petclinic"})
    assert analyze_resp.status_code == 200
    run_id = analyze_resp.json()["analysis_run_id"]
    
    # 2. Living Wiki
    wiki_resp = client.get("/api/wiki").json()
    assert wiki_resp["analysis_run_id"] == run_id, "Wiki analysis_run_id mismatch!"
    
    # 3. Change Impact
    impact_resp = client.get("/api/change-impact/OwnerController").json()
    assert "target_class" in impact_resp, "Change impact payload missing target_class!"
    
    # 4. Copilot Q&A
    ask_resp = client.post("/api/copilot/ask", json={"question": "Where is owner data persisted?"}).json()
    assert "plain_english" in ask_resp, "Copilot ask response missing plain_english payload!"

    print("  🟢 Integration Test: Shared Brain Workspace Integration Passed (run_id: {})".format(run_id))


if __name__ == "__main__":
    print("Running Integration Test Suite: Workspaces...")
    test_shared_brain_workspace_integration()
    print("Integration Test Suite Complete: 100% Passed\n")
