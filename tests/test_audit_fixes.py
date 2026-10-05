"""Regression tests for full-corner audit fixes (backend logic)."""
from devlensx.agents.security_agent import SecurityAgent
from devlensx.agents.architecture_agent import ArchitectureAgent
from devlensx.agents.change_impact_agent import ChangeImpactAgent
from devlensx.critic import CriticAgent
from devlensx.critic.claim_verifier import ClaimVerifierEngine
from devlensx.recommendation import RecommendationEngine


def _java_model():
    return {
        "repo": "shop",
        "repo_summary": {"language": "Java"},
        "stats": {"files_parsed": 2},
        "classes": [
            {"name": "OrderController", "stereotype": "Controller", "kind": "class",
             "file": "shop/OrderController.java", "package": "shop",
             "line_start": 1, "line_end": 60, "annotations": ["Controller"], "metadata": {}},
            {"name": "create", "stereotype": "Method", "kind": "method",
             "file": "shop/OrderController.java", "line_start": 20, "line_end": 40,
             "annotations": [], "is_test": False,
             "metadata": {"parent_class": "java_OrderController_1",
                          "parameters": [{"name": "order", "type": "Order"}]}},
            {"name": "OrderService", "stereotype": "Service", "kind": "class",
             "file": "shop/OrderService.java", "line_start": 1, "line_end": 50,
             "annotations": ["Service"], "metadata": {}},
            {"name": "Order", "stereotype": "Entity", "kind": "class",
             "file": "shop/Order.java", "line_start": 1, "line_end": 40,
             "annotations": ["Entity"], "metadata": {}},
            {"name": "OrderRepository", "stereotype": "Repository", "kind": "interface",
             "file": "shop/OrderRepository.java", "line_start": 1, "line_end": 20,
             "annotations": ["Repository"], "metadata": {}},
        ],
        "relationships": [
            {"source": "OrderController", "target": "OrderService", "type": "DEPENDS_ON"},
            {"source": "OrderService", "target": "OrderRepository", "type": "DEPENDS_ON"},
        ],
        "endpoints": [
            {"route": "/orders", "method": "POST", "handler": "java_OrderController_create_1",
             "file": "shop/OrderController.java"},
        ],
    }


def test_security_agent_no_crash_on_urm_schema():
    # URM classes carry no inline endpoints/methods: must not KeyError, and
    # model-level endpoints must still be inspected.
    res = SecurityAgent().analyze(_java_model(), ".", language="java")
    assert isinstance(res.get("findings", []), list)


def test_security_agent_flags_unprotected_post():
    res = SecurityAgent().analyze(_java_model(), ".", language="java")
    hits = [f for f in res["findings"] if f["category"] == "API Security"]
    assert hits, res["findings"]
    assert any(f["class_name"] == "OrderController" and "/orders" in f["title"] for f in hits)


def test_security_agent_method_annotation_counts():
    model = _java_model()
    model["classes"][1]["annotations"] = ["PostMapping", "PreAuthorize"]
    res = SecurityAgent().analyze(model, ".", language="java")
    assert not [f for f in res["findings"]
                if f["category"] == "API Security" and "OrderController" in f["title"]]


def test_architecture_god_class_uses_method_index():
    model = _java_model()
    for i in range(16):
        model["classes"].append({
            "name": f"op{i}", "stereotype": "Method", "kind": "method",
            "file": "shop/OrderService.java", "line_start": 60 + i, "line_end": 61 + i,
            "annotations": [], "is_test": False,
            "metadata": {"parent_class": "java_OrderService_2"},
        })
    class _G:
        def query_architecture_flow(self):
            return []

        def query_blast_radius(self, limit=10):
            return []

    res = ArchitectureAgent(graph_store=_G()).analyze(model)
    assert any(g["class_name"] == "OrderService" for g in res["god_classes"])


def test_coupling_finding_carries_file():
    class _G:
        def query_architecture_flow(self):
            return []

        def query_blast_radius(self, limit=10):
            return [{"class_name": "OrderService", "stereotype": "Service", "incoming_dependents": 4}]

    res = ArchitectureAgent(graph_store=_G()).analyze(_java_model())
    coupling = [f for f in res["findings"] if f["category"] == "Coupling"]
    assert coupling and coupling[0]["file"] == "shop/OrderService.java"


def test_critic_endpoint_containment_direction():
    agent = CriticAgent(None)
    finding = {
        "class_name": "OrderController", "file": "shop/OrderController.java",
        "category": "API Security",
        "evidence": {"endpoint": "POST /orders"},
    }
    res = agent.verify_finding(finding, _java_model())
    assert res["verdict"] == "VERIFIED", res


def test_critic_rejects_unknown_endpoint():
    agent = CriticAgent(None)
    finding = {
        "class_name": "OrderController", "file": "shop/OrderController.java",
        "category": "API Security",
        "evidence": {"endpoint": "DELETE /never-existed"},
    }
    res = agent.verify_finding(finding, _java_model())
    assert res["verdict"] == "REJECTED", res


def test_critic_extends_list_membership():
    agent = CriticAgent(None)
    model = _java_model()
    model["classes"].append({
        "name": "SpecialOrder", "stereotype": "Entity", "kind": "class",
        "file": "shop/SpecialOrder.java", "line_start": 1, "line_end": 20,
        "annotations": [], "extends": ["BaseOrder", "Order"], "metadata": {},
    })
    finding = {
        "class_name": "SpecialOrder", "file": "shop/SpecialOrder.java",
        "category": "Architecture", "evidence": {"extends_class": "Order"},
    }
    assert agent.verify_finding(finding, model)["verdict"] == "VERIFIED"
    finding["evidence"] = {"extends_class": "Unrelated"}
    assert agent.verify_finding(finding, model)["verdict"] == "REJECTED"


def test_claim_verifier_inheritance_requires_evidence():
    classes = [
        {"name": "A", "file": "a.py", "annotations": [], "extends": ["Base"]},
        {"name": "Base", "file": "b.py", "annotations": []},
    ]
    ok = ClaimVerifierEngine.extract_and_verify_claims("A extends Base.", classes, [])
    assert ok["verified_claims_count"] == 1
    bad = ClaimVerifierEngine.extract_and_verify_claims("A extends Unrelated.", classes, [])
    assert bad["verified_claims_count"] == 0


def test_claim_counts_add_up():
    res = ClaimVerifierEngine.extract_and_verify_claims(
        "Foo calls Bar. This system uses Redis for caching.", [{"name": "Foo", "file": "f.py"}], [])
    assert res["total_claims_analyzed"] == res["verified_claims_count"] + res["unsupported_claims_count"]


def test_recommendation_accepts_emoji_verdicts_and_no_crash_on_sparse():
    eng = RecommendationEngine()
    out = eng.synthesize([
        {"verdict": "🟢 VERIFIED", "category": "Maintainability", "severity": "HIGH",
         "title": "t", "class_name": "C", "file": "f", "claim": "c",
         "evidence_ratio": "1/2", "evidence_coverage_score": 50.0, "evidence_trail": {}},
    ], {"stats": {"files_parsed": 1}, "repo_summary": {"language": "Java"}})
    assert out["total_verified_findings"] == 1
    assert out["top_engineering_recommendations"][0]["affected_components"] == ["C"]


def test_recommendation_all_rejected_scores_zero_coverage():
    eng = RecommendationEngine()
    out = eng.synthesize(
        [{"verdict": "REJECTED", "category": "Coupling", "severity": "MEDIUM",
          "title": "t", "class_name": "C", "file": "f", "claim": "c"}],
        {"stats": {"files_parsed": 3}, "repo_summary": {"language": "Python"}})
    assert out["repository_intelligence_score"]["sub_scores"]["evidence_coverage"] == 0.0


def test_graph_build_populates_nodes_and_edges():
    from devlensx.graph import KuzuGraphStore
    store = KuzuGraphStore()
    stats = store.build_from_model(_java_model())
    assert stats["DEPENDS_ON"] == 2, stats
    assert len(store.query_subgraph_triples(max_nodes=10)) == 2
    callers = store.query_change_impact("OrderService")
    assert any((r.get("caller") or r.get("class_name")) == "OrderController" for r in callers)
    top = store.query_blast_radius(limit=5)
    assert top[0]["class_name"] in ("OrderService", "OrderRepository")
