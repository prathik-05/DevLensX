"""
DevLensX D7 End-to-End Documentation Browser Journey Test Suite
Validates the full user journey:
Wiki -> Page Catalog -> Select Page (Overview / Architecture) -> Inspect Claims & Verdicts -> Click Citation -> Resolve Exact Source Lines in D5 SourceViewer -> Multi-Repo Isolation Check.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from devlensx.api.main import app, global_state
from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.documentation.page_generator import DocumentationPageGenerator
from devlensx.documentation.cache import get_documentation_cache


def test_d7_documentation_browser_journey():
    print("=========================================================================")
    print("🚀 DEVLENSX D7: AUTOMATED DOCUMENTATION BROWSER JOURNEY & EVIDENCE FLOW")
    print("=========================================================================\n")

    client = TestClient(app)

    # 1. Analyze Spring PetClinic repository
    repo_path = os.path.abspath("eval_repos/spring-petclinic")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    model = intel.model
    run_id = "run_d7_journey_001"

    snapshot = register_snapshot(
        repository_id="spring-petclinic",
        analysis_run_id=run_id,
        repo_path=repo_path,
        commit_hash="c0ffee1",
    )

    # Generate and cache D7 pages
    gen = DocumentationPageGenerator(snapshot, model, retriever=intel.retriever)
    pages = gen.generate_all_pages()
    get_documentation_cache().store_pages("spring-petclinic", run_id, "c0ffee1", pages)

    global_state["repo_model"] = model
    global_state["analysis_run_id"] = run_id

    # 2. Browser Navigation: Wiki Tab -> Fetch Verified Pages Catalog
    res_pages = client.get(f"/api/wiki/{run_id}/pages")
    assert res_pages.status_code == 200, f"Failed to fetch wiki pages: {res_pages.text}"
    catalog_data = res_pages.json()
    assert catalog_data["count"] > 0
    print(f"  🟢 1. Wiki Catalog Fetched: {catalog_data['count']} verified documentation pages available.")

    # 3. User Interaction: Open Specific Page -> Core Architecture
    first_page_id = catalog_data["pages"][0]["id"]
    res_page = client.get(f"/api/wiki/{run_id}/pages/{first_page_id}")
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert len(page_data["sections"]) > 0
    print(f"  🟢 2. Page Opened: '{page_data['title']}' ({page_data['status']}) with {len(page_data['sections'])} sections.")

    # 4. Inspect Sections & Claims
    first_section = page_data["sections"][0]
    assert first_section["verdict"] in ("VERIFIED", "VERIFIED_WITH_SUGGESTIONS", "AI_SUGGESTION", "PARTIALLY_VERIFIED")
    print(f"  🟢 3. Section Inspected: '{first_section['heading']}' -> Verdict: {first_section['verdict']}")

    # 5. User Action: Click Citation -> Resolves via D5 EvidenceResolver
    sample_ref = None
    for s in page_data["sections"]:
        if s.get("evidence_refs"):
            sample_ref = s["evidence_refs"][0]
            break

    assert sample_ref is not None, "No evidence refs found on page to test citation resolution"
    print(f"  🟢 4. Citation Clicked: {sample_ref['file_path']}#L{sample_ref['line_start']}")

    res_ev = client.post("/api/evidence/resolve", json={
        "repository_id": sample_ref["repository_id"],
        "analysis_run_id": sample_ref["analysis_run_id"],
        "commit_hash": sample_ref.get("commit_hash"),
        "file_path": sample_ref["file_path"],
        "line_start": sample_ref["line_start"],
        "line_end": sample_ref["line_end"],
        "context_lines": 5,
    })
    assert res_ev.status_code == 200
    ev_data = res_ev.json()
    assert ev_data["resolved"] is True
    assert ev_data["status"] == "RESOLVED"
    assert len(ev_data["lines"]) > 0
    print(f"  🟢 5. [Open Source] Verified: SourceViewer rendered {len(ev_data['lines'])} lines of {sample_ref['file_path']}.")

    # 6. Multi-Tenant Cross-Repository Isolation Check
    cross_res = client.post("/api/evidence/resolve", json={
        "repository_id": "isolated-other-repo",
        "analysis_run_id": run_id,
        "commit_hash": "c0ffee1",
        "file_path": sample_ref["file_path"],
        "line_start": sample_ref["line_start"],
        "line_end": sample_ref["line_end"],
    })
    assert cross_res.status_code == 200
    assert cross_res.json()["resolved"] is False
    assert cross_res.json()["status"] == "PATH_VIOLATION"
    print("  🟢 6. Cross-Repository Isolation Verified: Unauthorized documentation evidence access blocked.")

    print("\n=========================================================================")
    print("🟢 DEVLENSX D7 BROWSER JOURNEY VERIFIED: 100% SUCCESS")
    print("=========================================================================\n")


if __name__ == "__main__":
    test_d7_documentation_browser_journey()
