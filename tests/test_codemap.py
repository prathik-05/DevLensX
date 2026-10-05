"""
Test Codemap — tour stops ordered by centrality/blast-radius
Fixed behavior: blast-radius ordering deterministic, grounding via graph, no LLM topology
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.codemap import build_codemap_stops, get_codemap_stops, cache_codemap_stops
from devlensx.critic import CriticAgent

def _setup():
    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    g = intel.graph_store
    snap = register_snapshot("spring-petclinic", "run_codemap_test", "eval_repos/spring-petclinic", "abc123")
    return model, g, snap

def test_codemap_non_empty_and_ordered():
    model, g, snap = _setup()
    stops = build_codemap_stops(model, g, "run_codemap_test")
    assert len(stops) > 0, "Codemap empty"
    # Ordered by blast-radius descending (fixed ordering)
    scores = [s["blast_radius"] for s in stops]
    assert scores == sorted(scores, reverse=True), f"Not ordered by blast-radius: {scores[:10]}"
    for s in stops[:3]:
        assert s.get("file"), "missing file"
        assert s.get("class_name"), "missing class_name"
        assert s.get("annotation"), "missing annotation"
        assert s.get("jump_link"), "missing jump_link"
        assert "#L" in s["jump_link"] or "/" in s["jump_link"]
    print(f"  codemap ordered OK stops={len(stops)}")

def test_codemap_determinism():
    """Determinism: same input -> same blast-radius ordering and same mermaid-like stops."""
    model, g, snap = _setup()
    stops1 = build_codemap_stops(model, g, "run_codemap_determinism")
    stops2 = build_codemap_stops(model, g, "run_codemap_determinism")
    assert [s["class_name"] for s in stops1] == [s["class_name"] for s in stops2], "Codemap not deterministic"
    assert [s["blast_radius"] for s in stops1] == [s["blast_radius"] for s in stops2], "Blast-radius not deterministic"
    assert [s["jump_link"] for s in stops1] == [s["jump_link"] for s in stops2], "Jump links not deterministic"
    print("  codemap determinism OK")

def test_codemap_no_llm_topology():
    """Verify codemap never calls LLM for topology (no prompt injection)."""
    import pathlib
    src = pathlib.Path("devlensx/codemap.py").read_text(encoding="utf-8", errors="ignore")
    assert "call_external_llm" not in src, "codemap.py must not call LLM for topology"
    assert "openai" not in src.lower() or "import openai" not in src, "codemap must not import LLM"
    # Verify it reuses ChangeImpact scoring via query_blast_radius
    assert "query_blast_radius" in src, "codemap must reuse ChangeImpact scoring"
    print("  codemap no LLM topology OK")

def test_get_codemap_stops_api():
    from fastapi.testclient import TestClient
    from devlensx.api.main import app, global_state
    from devlensx.repository_memory import RepositoryIntelligenceEngine
    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    g = intel.graph_store
    snap = register_snapshot("spring-petclinic", "run_codemap_api_test", "eval_repos/spring-petclinic", "abc123")
    stops = build_codemap_stops(model, g, "run_codemap_api_test")
    cache_codemap_stops("run_codemap_api_test", stops)
    client = TestClient(app)
    resp = client.get("/api/codemap/run_codemap_api_test")
    assert resp.status_code==200, resp.text
    data = resp.json()
    assert "stops" in data
    assert len(data["stops"]) > 0
    scores = [s["blast_radius"] for s in data["stops"]]
    assert scores == sorted(scores, reverse=True)
    print("  API codemap OK")

def test_codemap_reuses_changeimpact_scoring():
    model, g, snap = _setup()
    from devlensx.agents import ChangeImpactAgent
    impact_agent = ChangeImpactAgent(g)
    blast = impact_agent.graph_store.query_blast_radius(limit=5) if g else []
    stops = build_codemap_stops(model, g, "run_codemap_test2")
    if blast:
        top_name = blast[0]["class_name"]
        assert stops[0]["class_name"]==top_name, f"Top codemap {stops[0]['class_name']} != blast {top_name}"
    else:
        assert len(stops)>0
    print("  changeImpact scoring reuse OK")

if __name__ == "__main__":
    test_codemap_non_empty_and_ordered()
    test_codemap_determinism()
    test_codemap_no_llm_topology()
    test_get_codemap_stops_api()
    test_codemap_reuses_changeimpact_scoring()
    print("test_codemap passed")
