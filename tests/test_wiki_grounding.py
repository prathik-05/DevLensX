"""
Test Wiki Grounding — rejection of ungrounded content, nodeId/findingId refs, evidence-first
Fixed: verdict tautology removed — exact match Verdict enum, grounding rejection, XSS, empty-citation, no LLM
"""
import sys, os, html
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.wiki import generate_wiki_pages
from devlensx.critic import CriticAgent

def _setup():
    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    return intel.model, intel.graph_store

def test_every_claim_has_refs_and_lightweight_check():
    model, g = _setup()
    pages = generate_wiki_pages(model, g, [], "run_ground_test", "spring-petclinic", "abc123")
    for p in pages:
        for cit in p.citations:
            assert "nodeId" in cit or "findingId" in cit
        for sec in p.sections:
            verdict = sec.get("verdict")
            # FIXED: exact match Verdict enum — previously "Unverified".contains("Verified") tautology via `in str(verdict)`
            # Now strict equality, no substring shadowing
            assert verdict in ("Verified", "Unverified"), f"Bad verdict {verdict!r} — must be exactly Verified or Unverified, no tautology"
            # Ensure not using substring containment trick
            assert verdict == "Verified" or verdict == "Unverified", f"Verdict must be exact enum, got {verdict!r}"
    print("  claims refs and verdicts OK (exact Verdict enum)")

def test_rejection_of_ungrounded_content():
    model, g = _setup()
    critic = CriticAgent(g)
    fake_finding = {"class_name": "NonExistentPaymentGateway", "file": "com/example/NonExistentPaymentGateway.java", "category": "Architecture", "evidence": {}}
    res = critic.verify_finding(fake_finding, model)
    assert res["verdict"]=="REJECTED", "Fake class not rejected"
    fake_verified = [{"class_name":"NonExistentPaymentGateway","file":"fake","title":"Fake","category":"Change Impact","claim":"fake","verdict":"REJECTED","evidence":{}}]
    pages = generate_wiki_pages(model, g, fake_verified, "run_ground_fake", "spring-petclinic", "abc123")
    impact = next(p for p in pages if p.type=="impact")
    # Hallucinated node must not be stored as verified; filtered out -> empty citations -> Unverified placeholder
    for cit in impact.citations:
        assert cit.get("nodeId") != "NonExistentPaymentGateway", "Hallucinated node should be filtered from citations"
    # If hallucinated slipped through, badge must be Unverified
    for p in pages:
        for cit in p.citations:
            if cit.get("nodeId")=="NonExistentPaymentGateway":
                for s in p.sections:
                    assert s.get("verdict") != "Verified", "Hallucinated node marked Verified — must be Unverified"
    # Also verify empty-citation not Verified
    if len(impact.citations) == 0:
        for badge in impact.badges:
            assert badge.get("verdict") != "Verified", "Empty-citation Change Impact must not be Verified"
    print("  rejection of ungrounded OK")

def test_mermaid_via_template_not_llm():
    model, g = _setup()
    pages = generate_wiki_pages(model, g, [], "run_ground_mermaid", "spring-petclinic", "abc123")
    arch = next(p for p in pages if p.type=="architecture")
    known = {"OwnerController","PetController","VetController"}
    # Verify template grounding
    assert arch.mermaid.startswith("graph TD")
    assert "Redis" not in arch.mermaid, "Hallucinated Redis in mermaid"
    assert "Kafka" not in arch.mermaid, "Hallucinated Kafka in mermaid"
    # Verify no LLM used for topology
    import pathlib
    wiki_src = pathlib.Path("devlensx/wiki.py").read_text(encoding="utf-8", errors="ignore")
    codemap_src = pathlib.Path("devlensx/codemap.py").read_text(encoding="utf-8", errors="ignore")
    assert "call_external_llm" not in wiki_src, "wiki must not call LLM for mermaid"
    assert "call_external_llm" not in codemap_src, "codemap must not call LLM for topology"
    # Verify wiki uses html.escape via security helper
    assert "html.escape" in wiki_src or "wiki_content_sanitize" in wiki_src or "_html.escape" in wiki_src, "wiki must sanitize via html.escape"
    print("  mermaid template grounding OK (no LLM)")

def test_wiki_xss_sanitization_via_grounding():
    """XSS via wiki heading/content must be escaped, not stored raw."""
    model, g = _setup()
    payload = "<img src=x onerror=alert(1)>"
    xss_finding = {
        "class_name": "OwnerController",
        "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
        "title": payload,
        "category": "Change Impact",
        "claim": payload,
        "reason": payload,
        "evidence": {},
    }
    pages = generate_wiki_pages(model, g, [xss_finding], "run_ground_xss", "spring-petclinic", "abc123")
    impact = next(p for p in pages if p.type=="impact")
    for sec in impact.sections:
        assert "<img" not in sec.get("heading",""), "XSS heading not sanitized"
        assert "<img" not in sec.get("content",""), "XSS content not sanitized"
        # html.escape check
        if "img" in sec.get("heading","") or "img" in sec.get("content",""):
            assert "&lt;img" in sec.get("heading","") or "&lt;img" in sec.get("content",""), "Must be html.escape'd"
    from devlensx.core.security import wiki_content_sanitize
    assert "<img" not in wiki_content_sanitize(payload)
    assert "&lt;img" in wiki_content_sanitize(payload)
    print("  XSS sanitization OK")

def test_no_prompt_injection_via_llm_prose():
    """LLM prose must not inject topology — wiki/codemap never call LLM."""
    import pathlib, re
    wiki_src = pathlib.Path("devlensx/wiki.py").read_text(encoding="utf-8")
    codemap_src = pathlib.Path("devlensx/codemap.py").read_text(encoding="utf-8")
    # No LLM imports or calls
    for src, name in [(wiki_src, "wiki.py"), (codemap_src, "codemap.py")]:
        assert "call_external_llm" not in src, f"{name} must not call LLM"
        assert "call_llm" not in src.lower() or "claim_verifier" in src.lower(), f"{name} suspicious LLM call"
        # Ensure not using openai/groq/ollama for topology
        assert not re.search(r"from devlensx\.agents\.llm_client import", src), f"{name} must not import llm_client"
    # Verify ClaimVerifierEngine blocks hallucinations, not LLM
    model, g = _setup()
    bad_claim = "Redis manages data and Kafka routes messages"
    pages = generate_wiki_pages(model, g, [{"class_name":"OwnerController","file":"src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java","title":"Bad","category":"Change Impact","claim":bad_claim,"evidence":{}}], "run_injection", "spring-petclinic", "abc123")
    # If claim contains hallucinated tech, lightweight check should mark Unverified and filter
    impact = next(p for p in pages if p.type=="impact")
    # Should either be filtered (0 citations) or Unverified — never Verified with hallucinated tech
    for cit in impact.citations:
        for sec in impact.sections:
            if sec.get("nodeId")==cit.get("nodeId"):
                assert sec.get("verdict") != "Verified" or "redis" not in bad_claim.lower(), "Hallucinated tech claim must not be Verified"
    print("  no prompt injection via LLM prose OK")

if __name__ == "__main__":
    test_every_claim_has_refs_and_lightweight_check()
    test_rejection_of_ungrounded_content()
    test_mermaid_via_template_not_llm()
    test_wiki_xss_sanitization_via_grounding()
    test_no_prompt_injection_via_llm_prose()
    print("test_wiki_grounding passed")
