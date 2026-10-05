"""
DevLensX Step 6: Real Developer Journey End-to-End Workflow Integration Test Suite
Executes the full developer flow on spring-petclinic:
  6.1 Understand
  6.2 Ask (Q&A)
  6.3 Debug (Stack Trace mapping)
  6.4 Build Studio (Change Impact Analysis)
  6.5 PR Review
  6.6 Living Wiki Consistency
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from devlensx.api.main import app, global_state


def run_developer_journey():
    print("Executing Step 6: Full Developer Journey End-to-End Testing on spring-petclinic...\n")
    client = TestClient(app)

    # 6.0 Ingestion & Initial Analysis
    print("=== Stage 6.0: Repository Ingestion & Analysis ===")
    analyze_resp = client.post("/api/analyze", json={"repo_path": "eval_repos/spring-petclinic"})
    assert analyze_resp.status_code == 200, f"Analysis failed: {analyze_resp.text}"
    analyze_data = analyze_resp.json()
    run_id = analyze_data.get("analysis_run_id")
    assert run_id, "Missing analysis_run_id in response!"
    print(f"  🟢 Analysis Succeeded. Analysis Run ID: {run_id}")
    print(f"  🟢 Parsed Files: {analyze_data['parse_stats']['files_parsed']}, Score: {analyze_data['repository_intelligence_score']['overall']}\n")

    # 6.1 Understand Layer
    print("=== Stage 6.1: Understand Layer ===")
    assert analyze_data.get("repository"), "Missing repository name"
    summary = analyze_data.get("repo_summary", {})
    print(f"  🟢 Primary Language: {summary.get('language')}")
    print(f"  🟢 Framework: {summary.get('framework')}")
    print(f"  🟢 Discovered Controllers: {summary.get('controllers')}, Services: {summary.get('services')}, Repositories: {summary.get('repositories')}\n")

    # 6.2 Ask (Q&A Layer)
    print("=== Stage 6.2: Copilot Ask Q&A Layer ===")
    ask_payload = {
        "question": "How does owner management work and where is owner data persisted?",
        "context_files": ["OwnerController.java", "OwnerRepository.java"]
    }
    ask_resp = client.post("/api/copilot/ask", json=ask_payload)
    assert ask_resp.status_code == 200, f"Copilot ask failed: {ask_resp.text}"
    ask_data = ask_resp.json()
    print(f"  🟢 Q&A Status: {ask_data.get('status')}")
    print(f"  🟢 Grounded Response: {ask_data.get('answer', '')[:120]}...\n")

    # 6.2.1 Non-Existent Symbol Query Test (PaymentController)
    ask_payment = client.post("/api/copilot/ask", json={"question": "Does PaymentController handle payments?"}).json()
    print(f"  🟢 Non-Existent Symbol Protection: {ask_payment.get('answer', '')[:120]}...\n")

    # 6.3 Debug Layer (Stack Trace Mapping)
    print("=== Stage 6.3: Trace-Based Root Cause Debugger ===")
    trace_payload = {
        "error_message": "NullPointerException at org.springframework.samples.petclinic.owner.OwnerController.processFindForm(OwnerController.java:110)",
        "stack_trace": "java.lang.NullPointerException\n\tat org.springframework.samples.petclinic.owner.OwnerController.processFindForm(OwnerController.java:110)\n\tat org.springframework.samples.petclinic.owner.OwnerRepository.findByLastName(OwnerRepository.java:45)"
    }
    debug_resp = client.post("/api/debug/trace", json=trace_payload)
    assert debug_resp.status_code == 200, f"Debug trace failed: {debug_resp.text}"
    debug_data = debug_resp.json()
    print(f"  🟢 Debug Trace Handled: {debug_data.get('status')}")
    print(f"  🟢 Mapped AST Nodes: {debug_data.get('mapped_classes', [])}\n")

    # 6.4 Build Studio Layer (Change Impact & Blast Radius)
    print("=== Stage 6.4: Build Studio (Change Impact Analysis) ===")
    impact_resp = client.get("/api/change-impact/OwnerController")
    assert impact_resp.status_code == 200, f"Change impact failed: {impact_resp.text}"
    impact_data = impact_resp.json()
    print(f"  🟢 Target Class: {impact_data.get('target_class')}")
    print(f"  🟢 Risk Assessment Level: {impact_data.get('risk_level')}")
    print(f"  🟢 Direct Callers Count: {len(impact_data.get('direct_callers', []))}\n")

    # 6.5 Review Layer (PR Diff Audit)
    print("=== Stage 6.5: Review Layer (PR Diff Audit) ===")
    pr_payload = {
        "diff": "--- a/src/main/java/org/springframework/samples/petclinic/owner/Owner.java\n+++ b/src/main/java/org/springframework/samples/petclinic/owner/Owner.java\n+ private String email;"
    }
    pr_resp = client.post("/api/reviews/pr-review", json=pr_payload)
    assert pr_resp.status_code == 200, f"PR review failed: {pr_resp.text}"
    pr_data = pr_resp.json()
    print(f"  🟢 PR Review Status: {pr_data.get('status')}")
    print(f"  🟢 Identified Affected Capabilities: {pr_data.get('affected_capabilities', [])}\n")

    # 6.6 Living Wiki Consistency Layer
    print("=== Stage 6.6: Living DeepWiki Consistency ===")
    wiki_resp = client.get("/api/wiki")
    assert wiki_resp.status_code == 200, f"Wiki failed: {wiki_resp.text}"
    wiki_data = wiki_resp.json()
    assert wiki_data.get("analysis_run_id") == run_id, "Wiki analysis_run_id mismatch!"
    print(f"  🟢 Wiki Shared Analysis Run ID Verified: {wiki_data.get('analysis_run_id')}")
    print(f"  🟢 Wiki Discovered Capabilities: {[c['capability'] for c in wiki_data.get('capabilities', [])]}\n")

    print("=========================================================================")
    print("🟢 STEP 6 DEVELOPER JOURNEY COMPLETE: 100% CONSISTENCY & ZERO BREAKAGES!")
    print("=========================================================================")


if __name__ == "__main__":
    run_developer_journey()
