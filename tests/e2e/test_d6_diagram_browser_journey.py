"""
DevLensX D6 End-to-End Diagram Browser Journey Test Suite
Validates the full user journey:
Wiki / Architecture -> Select Diagram -> Click Node / Edge -> Inspect Evidence -> Resolve Exact Source Lines in D5 SourceViewer -> Multi-Repo Isolation Check.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from devlensx.api.main import app, global_state
from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot, get_evidence_resolver
from devlensx.diagrams.generator import generate_all_diagrams


def test_d6_diagram_browser_journey():
    print("=========================================================================")
    print("🚀 DEVLENSX D6: AUTOMATED DIAGRAM BROWSER JOURNEY & EVIDENCE FLOW")
    print("=========================================================================\n")

    client = TestClient(app)

    # 1. Analyze Spring PetClinic repository
    repo_path = os.path.abspath("eval_repos/spring-petclinic")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    model = intel.model
    run_id = "run_d6_journey_001"

    snapshot = register_snapshot(
        repository_id="spring-petclinic",
        analysis_run_id=run_id,
        repo_path=repo_path,
        commit_hash="c0ffee1",
    )
    diagrams = generate_all_diagrams(snapshot, model)
    global_state["repo_model"] = model
    global_state["analysis_run_id"] = run_id

    # 2. Browser Navigation: Architecture Tab -> Fetch Architecture Diagram
    res_arch = client.get(f"/api/diagrams/{run_id}/ARCHITECTURE")
    assert res_arch.status_code == 200, f"Failed to fetch architecture diagram: {res_arch.text}"
    arch_data = res_arch.json()
    assert arch_data["type"] == "ARCHITECTURE"
    assert len(arch_data["nodes"]) > 0
    assert arch_data["validation"]["valid"] is True
    print(f"  🟢 1. Architecture Diagram Fetched: {len(arch_data['nodes'])} nodes, {len(arch_data['edges'])} edges")

    # 3. User Interaction: Click Node -> OwnerController
    owner_node = next((n for n in arch_data["nodes"] if n["id"] == "OwnerController"), None)
    assert owner_node is not None, "OwnerController node missing in architecture diagram"
    assert len(owner_node["evidence_refs"]) > 0
    node_ref = owner_node["evidence_refs"][0]
    print(f"  🟢 2. Node Clicked: {owner_node['label']} -> EvidenceRef: {node_ref['file_path']}#L{node_ref['line_start']}")

    # 4. User Action: [Open Source] -> Triggers D5 Evidence Resolver
    res_node_ev = client.post("/api/evidence/resolve", json={
        "repository_id": node_ref["repository_id"],
        "analysis_run_id": node_ref["analysis_run_id"],
        "commit_hash": node_ref.get("commit_hash"),
        "file_path": node_ref["file_path"],
        "line_start": node_ref["line_start"],
        "line_end": node_ref["line_end"],
        "context_lines": 5,
    })
    assert res_node_ev.status_code == 200
    node_ev_data = res_node_ev.json()
    assert node_ev_data["resolved"] is True
    assert node_ev_data["status"] == "RESOLVED"
    assert len(node_ev_data["lines"]) > 0
    assert any("class OwnerController" in l["content"] or "OwnerController" in l["content"] for l in node_ev_data["lines"])
    print(f"  🟢 3. [Open Source] Resolved: SourceViewer rendered {len(node_ev_data['lines'])} lines of {node_ref['file_path']}")

    # 5. User Interaction: Fetch Dependency Diagram -> Click Edge
    res_dep = client.get(f"/api/diagrams/{run_id}/DEPENDENCY")
    assert res_dep.status_code == 200
    dep_data = res_dep.json()
    assert len(dep_data["edges"]) > 0

    first_edge = dep_data["edges"][0]
    assert len(first_edge["evidence_refs"]) > 0
    edge_ref = first_edge["evidence_refs"][0]
    print(f"  🟢 4. Edge Clicked: {first_edge['source']} --[{first_edge['relationship']}]--> {first_edge['target']}")

    res_edge_ev = client.post("/api/evidence/resolve", json={
        "repository_id": edge_ref["repository_id"],
        "analysis_run_id": edge_ref["analysis_run_id"],
        "commit_hash": edge_ref.get("commit_hash"),
        "file_path": edge_ref["file_path"],
        "line_start": edge_ref["line_start"],
        "line_end": edge_ref["line_end"],
    })
    assert res_edge_ev.status_code == 200
    assert res_edge_ev.json()["resolved"] is True
    print(f"  🟢 5. Edge Relationship Provenance Resolved via D5 SourceViewer.")

    # 6. Multi-Tenant / Cross-Repository Isolation Check
    cross_res = client.post("/api/evidence/resolve", json={
        "repository_id": "other-isolated-repo",
        "analysis_run_id": run_id,
        "commit_hash": "c0ffee1",
        "file_path": node_ref["file_path"],
        "line_start": node_ref["line_start"],
        "line_end": node_ref["line_end"],
    })
    assert cross_res.status_code == 200
    assert cross_res.json()["resolved"] is False
    assert cross_res.json()["status"] == "PATH_VIOLATION"
    print(f"  🟢 6. Cross-Repository Isolation Verified: Unauthorized evidence access strictly blocked.")

    print("\n=========================================================================")
    print("🟢 DEVLENSX D6 BROWSER JOURNEY VERIFIED: 100% SUCCESS")
    print("=========================================================================\n")


if __name__ == "__main__":
    test_d6_diagram_browser_journey()
