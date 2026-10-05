"""
Test Wiki Generation — determinism, mermaid correctness, page types, cache
Fixed behavior: determinism including mermaid, blast-radius ordering, grounding rejection, XSS sanitization, no LLM topology
"""
import sys, os, html
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.wiki import generate_wiki_pages, build_and_cache_wiki, get_wiki_tree, get_wiki_page, get_wiki_cache
from devlensx.critic import CriticAgent

def _setup_petclinic():
    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    g = intel.graph_store
    from devlensx.agents import ArchitectureAgent, ChangeImpactAgent
    arch = ArchitectureAgent(g).analyze(model)
    impact = ChangeImpactAgent(g).analyze(model)
    critic = CriticAgent(g)
    raw = arch["findings"] + impact["findings"]
    verified = critic.verify_all(raw, model)
    verified_only = [f for f in verified if f.get("verdict")=="VERIFIED"]
    if not verified_only:
        verified_only = raw
    snap = register_snapshot("spring-petclinic", "run_wiki_gen_test", "eval_repos/spring-petclinic", "abc123")
    return model, g, verified_only, snap

def test_wiki_determinism():
    model, g, verified, snap = _setup_petclinic()
    pages1 = generate_wiki_pages(model, g, verified, "run_wiki_gen_test", "spring-petclinic", "abc123")
    pages2 = generate_wiki_pages(model, g, verified, "run_wiki_gen_test", "spring-petclinic", "abc123")
    ids1 = [p.id for p in pages1]
    ids2 = [p.id for p in pages2]
    assert ids1 == ids2, "Wiki page ids not deterministic"
    cites1 = [(c.get("nodeId"), c.get("file")) for p in pages1 for c in p.citations]
    cites2 = [(c.get("nodeId"), c.get("file")) for p in pages2 for c in p.citations]
    assert cites1 == cites2, "Citations not deterministic"
    # Determinism including mermaid (fixed behavior)
    mermaids1 = [(p.id, p.mermaid) for p in pages1]
    mermaids2 = [(p.id, p.mermaid) for p in pages2]
    assert mermaids1 == mermaids2, "Mermaid not deterministic across runs"
    # Also check that mermaid ordering is deterministic (same edges order)
    arch1 = next(p for p in pages1 if p.type=="architecture")
    arch2 = next(p for p in pages2 if p.type=="architecture")
    assert arch1.mermaid == arch2.mermaid, "Architecture mermaid not deterministic"
    for p1, p2 in zip([p for p in pages1 if p.type=="module"], [p for p in pages2 if p.type=="module"]):
        assert p1.mermaid == p2.mermaid, f"Module {p1.id} mermaid not deterministic"
    print("  deterministic OK (including mermaid)")

def test_wiki_page_types_present():
    model, g, verified, snap = _setup_petclinic()
    pages = generate_wiki_pages(model, g, verified, "run_wiki_gen_test", "spring-petclinic", "abc123")
    types = {p.type for p in pages}
    assert "overview" in types, "Overview missing"
    assert "architecture" in types, "Architecture missing"
    assert "module" in types, "Module pages missing"
    assert "api" in types, "API Reference missing"
    assert "impact" in types, "Change Impact missing"
    mods = [p for p in pages if p.type=="module"]
    assert len(mods) >= 2, f"Expected >=2 module pages, got {len(mods)}"
    print(f"  page types OK: {types} modules={len(mods)}")

def test_mermaid_correctness_petclinic():
    model, g, verified, snap = _setup_petclinic()
    pages = generate_wiki_pages(model, g, verified, "run_wiki_gen_test", "spring-petclinic", "abc123")
    arch = next(p for p in pages if p.type=="architecture")
    assert arch.mermaid is not None
    assert arch.mermaid.startswith("graph TD"), f"Mermaid not graph TD: {arch.mermaid[:100]}"
    assert "-->" in arch.mermaid, "No edges in system dependency mermaid"
    mods = [p for p in pages if p.type=="module"]
    for m in mods[:2]:
        assert m.mermaid is not None
        assert "classDiagram" in m.mermaid, f"Module mermaid not classDiagram: {m.id}"
    # Verify no LLM topology: mermaid derived from template, deterministic
    # Same input must produce same output (already checked in determinism), and no hallucinated tech
    assert "Redis" not in arch.mermaid and "Kafka" not in arch.mermaid, "Hallucinated tech in mermaid"
    print("  mermaid correctness OK (template, not LLM)")

def test_wiki_no_llm_topology():
    """Verify wiki never calls LLM for topology (no prompt injection via LLM prose)."""
    import pathlib
    wiki_src = pathlib.Path("devlensx/wiki.py").read_text(encoding="utf-8", errors="ignore")
    assert "call_external_llm" not in wiki_src, "wiki.py must not call LLM for topology"
    assert "openai" not in wiki_src.lower() or "openai" in wiki_src.lower() and "import openai" not in wiki_src, "wiki.py must not import LLM client for mermaid"
    # Ensure mermaid functions are template-based (contain graph TD / classDiagram)
    assert "graph TD" in wiki_src and "classDiagram" in wiki_src, "wiki.py must contain template mermaid strings"
    print("  wiki no LLM topology OK")

def test_wiki_heading_sanitization():
    """Verify wiki heading/content sanitization via html.escape prevents XSS."""
    model, g, verified, snap = _setup_petclinic()
    xss_payload = "<script>alert('xss')</script>"
    xss_finding = {
        "class_name": "OwnerController",
        "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
        "title": xss_payload,
        "category": "Change Impact",
        "claim": f"Impact of {xss_payload} should be escaped",
        "reason": xss_payload,
        "evidence": {},
        "verdict": "VERIFIED"
    }
    # OwnerController exists, so lightweight check will pass, but heading/content must be escaped
    pages = generate_wiki_pages(model, g, [xss_finding], "run_wiki_xss_test", "spring-petclinic", "abc123")
    impact = next(p for p in pages if p.type=="impact")
    # No raw script tags should survive
    for sec in impact.sections:
        heading = sec.get("heading","")
        content = sec.get("content","")
        assert "<script>" not in heading, f"XSS not sanitized in heading: {heading}"
        assert "<script>" not in content, f"XSS not sanitized in content: {content}"
        if "script" in heading.lower():
            assert "&lt;script&gt;" in heading or "script" not in heading.lower(), "Heading not escaped via html.escape"
    # Verify via security helper
    from devlensx.core.security import wiki_content_sanitize, wiki_heading_sanitize
    assert wiki_heading_sanitize(xss_payload) == html.escape(xss_payload)[:200]
    assert wiki_content_sanitize(xss_payload) == html.escape(xss_payload)[:2000]
    assert "<script>" not in wiki_content_sanitize(xss_payload)
    print("  wiki XSS sanitization OK")

def test_wiki_change_impact_empty_citation_not_verified():
    """Ensure wiki Change Impact empty-citation page not stored as Verified (evidence-first)."""
    model, g, verified, snap = _setup_petclinic()
    # No verified findings -> empty citation placeholder
    pages = generate_wiki_pages(model, g, [], "run_wiki_empty_impact", "spring-petclinic", "abc123")
    impact = next(p for p in pages if p.type=="impact")
    # When citations empty, verdict must NOT be Verified
    if len(impact.citations) == 0:
        for sec in impact.sections:
            if sec.get("heading") == "No High-Impact Findings":
                assert sec.get("verdict") != "Verified", "Empty-citation Change Impact page must not be stored as Verified"
        for badge in impact.badges:
            if badge.get("section") == "No High-Impact Findings":
                assert badge.get("verdict") != "Verified", "Empty-citation badge must not be Verified"
    # Also test with hallucinated findings that get filtered -> empty
    fake = [{"class_name":"NonExistentXYZ","file":"fake","title":"Fake Impact","category":"Change Impact","claim":"fake","verdict":"REJECTED","evidence":{}}]
    pages2 = generate_wiki_pages(model, g, fake, "run_wiki_empty2", "spring-petclinic", "abc123")
    impact2 = next(p for p in pages2 if p.type=="impact")
    if len(impact2.citations) == 0:
        assert all(b.get("verdict") != "Verified" for b in impact2.badges if b.get("section")=="No High-Impact Findings"), "Filtered empty impact must not be Verified"
    print("  empty-citation not Verified OK")

def test_cache_keyed_and_invalidation():
    model, g, verified, snap = _setup_petclinic()
    pages = build_and_cache_wiki(model, g, verified, "run_wiki_cache_test", "spring-petclinic", "abc123")
    tree = get_wiki_tree("run_wiki_cache_test")
    assert tree is not None and tree["count"]==len(pages)
    pages2 = build_and_cache_wiki(model, g, verified, "run_wiki_cache_test2", "spring-petclinic", "abc123")
    tree2 = get_wiki_tree("run_wiki_cache_test2")
    assert tree2["analysis_id"]=="run_wiki_cache_test2"
    from devlensx.wiki import invalidate_wiki_repo
    invalidate_wiki_repo("spring-petclinic", "abc123")
    assert get_wiki_tree("run_wiki_cache_test") is None
    print("  cache invalidation OK")

def test_api_endpoints():
    from fastapi.testclient import TestClient
    from devlensx.api.main import app
    model, g, verified, snap = _setup_petclinic()
    build_and_cache_wiki(model, g, verified, "run_wiki_api_test", "spring-petclinic", "abc123")
    client = TestClient(app)
    resp = client.get("/api/wiki/run_wiki_api_test")
    assert resp.status_code==200, resp.text
    data = resp.json()
    assert "page_tree" in data or "count" in data
    assert data.get("analysis_id")=="run_wiki_api_test" or "page_tree" in data
    tree = get_wiki_tree("run_wiki_api_test")
    pid = tree["page_tree"][0]["id"] if tree else "overview"
    resp2 = client.get(f"/api/wiki/run_wiki_api_test/page/{pid}")
    assert resp2.status_code==200, resp2.text
    print("  API endpoints OK")

if __name__ == "__main__":
    test_wiki_determinism()
    test_wiki_page_types_present()
    test_mermaid_correctness_petclinic()
    test_wiki_no_llm_topology()
    test_wiki_heading_sanitization()
    test_wiki_change_impact_empty_citation_not_verified()
    test_cache_keyed_and_invalidation()
    test_api_endpoints()
    print("test_wiki_generation passed")
