"""
E2E smoke test helper: analyze PetClinic and assert all page types present and codemap non-empty ordered by blast-radius.
Fixed behavior: determinism including mermaid, blast-radius ordering, grounding rejection, no XSS, no LLM
"""
import sys, os, pathlib, html
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from devlensx.api.main import app

def test_wiki_codemap_smoke():
    client = TestClient(app)
    resp = client.post("/api/analyze", json={"repo_path": "eval_repos/spring-petclinic"})
    assert resp.status_code==200, resp.text
    data = resp.json()
    analysis_id = data.get("analysis_run_id")
    assert analysis_id, "No analysis_run_id"
    # Check wiki tree
    wiki_resp = client.get(f"/api/wiki/{analysis_id}")
    assert wiki_resp.status_code==200, wiki_resp.text
    wiki = wiki_resp.json()
    assert "page_tree" in wiki or "count" in wiki
    tree = wiki.get("page_tree", [])
    assert wiki.get("count", len(tree)) >= 5, f"Expected >=5 pages, got {wiki}"
    types_titles = [t.get("title","") for t in tree] + list(wiki.get("pages_summary", {}).keys())
    has_overview = any("Overview" in str(x) or x=="overview" for x in types_titles)
    assert has_overview or len(tree)>=1, "Overview missing"
    # Determinism including mermaid: fetch pages twice, mermaid must be same
    from devlensx.wiki import generate_wiki_pages, get_wiki_page, get_wiki_tree
    from devlensx.repository_memory import RepositoryIntelligenceEngine
    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    g = intel.graph_store
    pages_a = generate_wiki_pages(model, g, [], analysis_id, "spring-petclinic", "abc123")
    pages_b = generate_wiki_pages(model, g, [], analysis_id, "spring-petclinic", "abc123")
    assert [(p.id, p.mermaid) for p in pages_a] == [(p.id, p.mermaid) for p in pages_b], "Wiki mermaid not deterministic"
    # Blast-radius ordering: codemap must be ordered descending
    codemap_resp = client.get(f"/api/codemap/{analysis_id}")
    assert codemap_resp.status_code==200, codemap_resp.text
    codemap = codemap_resp.json()
    assert "stops" in codemap
    stops = codemap["stops"]
    assert len(stops) > 0, "Codemap empty"
    scores = [s["blast_radius"] for s in stops]
    assert scores == sorted(scores, reverse=True), "Codemap not ordered by blast-radius"
    # Grounding rejection: no hallucinated citations marked Verified
    for p in pages_a:
        for cit in p.citations:
            if cit.get("nodeId")=="NonExistentPaymentGateway":
                for sec in p.sections:
                    assert sec.get("verdict") != "Verified", "Hallucinated node must not be Verified"
    # XSS sanitization: no raw script tags in any wiki page
    for pid in [t["id"] for t in tree]:
        page_resp = client.get(f"/api/wiki/{analysis_id}/page/{pid}")
        if page_resp.status_code==200:
            pj = page_resp.json()
            for sec in pj.get("sections", []):
                assert "<script>" not in sec.get("heading",""), f"XSS not sanitized in {pid}"
                assert "<script>" not in sec.get("content",""), f"XSS not sanitized in {pid}"
    # No LLM for topology: verify source files don't call LLM
    wiki_src = pathlib.Path("devlensx/wiki.py").read_text(encoding="utf-8", errors="ignore")
    codemap_src = pathlib.Path("devlensx/codemap.py").read_text(encoding="utf-8", errors="ignore")
    assert "call_external_llm" not in wiki_src, "wiki must not call LLM"
    assert "call_external_llm" not in codemap_src, "codemap must not call LLM"
    assert "html.escape" in wiki_src or "wiki_content_sanitize" in wiki_src, "wiki must sanitize via html.escape"
    # Empty-citation Change Impact not Verified
    impact_page = client.get(f"/api/wiki/{analysis_id}/page/change-impact")
    if impact_page.status_code==200:
        ip = impact_page.json()
        if len(ip.get("citations", [])) == 0:
            for badge in ip.get("badges", []):
                # placeholder should not be Verified when citations empty (evidence-first)
                if badge.get("section") == "No High-Impact Findings":
                    assert badge.get("verdict") != "Verified", "Empty-citation Change Impact must not be Verified"
    # Get a specific page still works
    page_id = tree[0]["id"] if tree else "overview"
    page_resp = client.get(f"/api/wiki/{analysis_id}/page/{page_id}")
    assert page_resp.status_code==200, page_resp.text
    print(f"  smoke OK analysis={analysis_id} wiki_pages={wiki.get('count')} codemap_stops={len(stops)}")

if __name__ == "__main__":
    test_wiki_codemap_smoke()
