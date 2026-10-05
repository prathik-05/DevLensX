"""P1-C impact-grounding tests: changed symbol -> graph/model neighborhood ->
affected set -> findings -> ClaimVerifier. No LLM in the affected path."""
from devlensx.review.grounding import (
    ground_diff, resolve_affected, build_change_mermaid, check_base_compat,
    EXACT_SNAPSHOT, BASE_MISMATCH, UNKNOWN_BASE,
)
from devlensx.review.hunks import HunkParser
from devlensx.review.symbol_resolver import resolve_changed_symbols
from devlensx.codereview import verify_candidates

MODEL = {
    "repo": "shop",
    "repo_summary": {"language": "java", "framework": "Spring Boot"},
    "classes": [
        {"name": "OrderController", "stereotype": "Controller", "kind": "class",
         "file": "shop/OrderController.java", "line_start": 1, "line_end": 120,
         "annotations": ["Controller"], "metadata": {}},
        {"name": "placeOrder", "stereotype": "Method", "kind": "method",
         "file": "shop/OrderService.java", "line_start": 40, "line_end": 80,
         "annotations": [], "is_test": False,
         "metadata": {"parent_class": "java_OrderService_1"}},
        {"name": "OrderService", "stereotype": "Service", "kind": "class",
         "file": "shop/OrderService.java", "line_start": 1, "line_end": 100,
         "annotations": ["Service"], "metadata": {}},
        {"name": "OrderRepository", "stereotype": "Repository", "kind": "interface",
         "file": "shop/OrderRepository.java", "line_start": 1, "line_end": 30,
         "annotations": ["Repository"], "metadata": {}},
        {"name": "StripeProcessor", "stereotype": "Component", "kind": "class",
         "file": "shop/StripeProcessor.java", "line_start": 1, "line_end": 60,
         "annotations": [], "metadata": {}, "implements": ["PaymentProcessor"]},
        {"name": "PaymentProcessor", "stereotype": "Component", "kind": "interface",
         "file": "shop/PaymentProcessor.java", "line_start": 1, "line_end": 20,
         "annotations": [], "metadata": {}},
        {"name": "PaymentGateway", "stereotype": "Component", "kind": "class",
         "file": "shop/PaymentGateway.java", "line_start": 1, "line_end": 50,
         "annotations": [], "metadata": {}},
        {"name": "OrderServiceTest", "stereotype": "Test", "kind": "class",
         "file": "shop/OrderServiceTest.java", "line_start": 1, "line_end": 40,
         "annotations": [], "is_test": True, "metadata": {}},
    ],
    "relationships": [
        {"source": "OrderController", "target": "OrderService", "type": "DEPENDS_ON"},
        {"source": "OrderService", "target": "OrderRepository", "type": "DEPENDS_ON"},
    ],
    "endpoints": [],
}

SNAP = {"repository_id": "shop", "analysis_run_id": "run_shop", "commit_hash": "c0ffee"}


def _diff(path, start, added=("n1",), removed=("o1",)):
    body = "".join(f"+{a}\n" for a in added) + "".join(f"-{r}\n" for r in removed)
    return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
            f"@@ -{start},3 +{start},{3 + len(added) - len(removed)} @@\n x\n{body} y\n")


class _FakeGraph:
    """Stand-in Kuzu store. Returns a caller, plus a cross-repo poison name."""
    def __init__(self, callers):
        self._callers = callers

    def query_change_impact(self, target):
        return [{"caller": c, "file": f"{c}.java"} for c in self._callers.get(target, [])]


def _changed(diff):
    return resolve_changed_symbols(HunkParser.parse(diff), MODEL)


# 1. changed method -> direct caller
def test_direct_caller_from_graph():
    diff = _diff("shop/OrderService.java", 40)
    changed = _changed(diff)
    assert {c.name for c in changed} == {"placeOrder"}
    aff = resolve_affected(changed, MODEL, SNAP, _FakeGraph({"placeOrder": ["OrderController"]}))
    hit = next(a for a in aff if a["target_symbol"] == "OrderController")
    assert hit["relationship"] == "CALLER_OF" and hit["via"] == "kuzu" and hit["hop"] == 1


# 2. transitive caller via model edges
def test_transitive_caller_model_edges():
    diff = _diff("shop/OrderRepository.java", 5, added=("q",))
    changed = _changed(diff)
    assert {c.name for c in changed} == {"OrderRepository"}
    aff = resolve_affected(changed, MODEL, SNAP, None)
    by_sym = {a["target_symbol"]: a for a in aff}
    assert by_sym["OrderService"]["hop"] == 1
    assert by_sym["OrderController"]["hop"] == 2


# 3. changed interface -> implementations
def test_interface_to_implementations():
    diff = _diff("shop/PaymentProcessor.java", 5, added=("m",))
    aff = resolve_affected(_changed(diff), MODEL, SNAP, None)
    hit = next(a for a in aff if a["target_symbol"] == "StripeProcessor")
    assert hit["relationship"] == "IMPLEMENTS"


# 4. changed dependency -> dependents
def test_dependency_to_dependents():
    diff = _diff("shop/OrderRepository.java", 5, added=("q",))
    aff = resolve_affected(_changed(diff), MODEL, SNAP, None)
    assert any(a["target_symbol"] == "OrderService" and a["relationship"] == "DEPENDENT_OF" for a in aff)


# 5. controller change reaches service/repository path (forward callees)
def test_controller_forward_path():
    diff = _diff("shop/OrderController.java", 10, added=("h",))
    aff = resolve_affected(_changed(diff), MODEL, SNAP, None)
    kinds = {a["target_symbol"]: a["relationship"] for a in aff}
    assert kinds.get("OrderService") == "DEPENDS_ON"
    assert kinds.get("OrderRepository") == "DEPENDS_ON"


# 6. associated tests
def test_associated_tests():
    diff = _diff("shop/OrderService.java", 40)
    aff = resolve_affected(_changed(diff), MODEL, SNAP, None)
    assert any(a["target_symbol"] == "OrderServiceTest" and a["relationship"] == "TESTS" for a in aff)


# 7. unrelated symbol excluded
def test_unrelated_excluded():
    diff = _diff("shop/PaymentGateway.java", 10, added=("z",))
    aff = resolve_affected(_changed(diff), MODEL, SNAP, None)
    names = {a["target_symbol"] for a in aff}
    assert "OrderService" not in names and "OrderController" not in names
    # sanity: the changed symbol itself resolved
    assert {c.name for c in _changed(diff)} == {"PaymentGateway"}


# 8. cross-repository graph isolation
def test_cross_repo_graph_hits_dropped():
    diff = _diff("shop/OrderService.java", 40)
    aff = resolve_affected(
        _changed(diff), MODEL, SNAP, _FakeGraph({"placeOrder": ["EvilExternal", "OrderController"]})
    )
    names = {a["target_symbol"] for a in aff}
    assert "EvilExternal" not in names
    assert "OrderController" in names


# 9/10. snapshot identity on refs + compat statuses
def test_base_compat_statuses():
    assert check_base_compat("c0ffee", SNAP)["status"] == EXACT_SNAPSHOT
    assert check_base_compat("c0ffee99", SNAP)["status"] == EXACT_SNAPSHOT  # prefix-tolerant
    assert check_base_compat("deadbeef", SNAP)["status"] == BASE_MISMATCH
    assert check_base_compat(None, SNAP)["status"] == UNKNOWN_BASE
    assert check_base_compat("c0ffee", {})["status"] == UNKNOWN_BASE


def test_refs_carry_snapshot_identity():
    diff = _diff("shop/OrderService.java", 40)
    aff = resolve_affected(_changed(diff), MODEL, SNAP, _FakeGraph({"placeOrder": ["OrderController"]}))
    for a in aff:
        for r in a["evidence_refs"]:
            assert (r["repository_id"], r["analysis_run_id"], r["commit_hash"]) == ("shop", "run_shop", "c0ffee")


# 11a. P1-J: entity existence is not claim support — a real edge verifies,
# while the same real symbols in a false relationship do not.
def test_real_relation_verified_vs_false_relation():
    from devlensx.codereview import verify_candidates
    true_claim = [{"severity": "HIGH", "title": "OrderController depends on OrderService",
                   "description": "OrderController depends on OrderService for checkout.",
                   "file": "", "line_start": 0, "line_end": 0, "category": "Architecture"}]
    false_claim = [{"severity": "HIGH", "title": "OrderService depends on OrderController",
                    "description": "OrderService depends on OrderController for checkout.",
                    "file": "", "line_start": 0, "line_end": 0, "category": "Architecture"}]
    good = verify_candidates(true_claim, MODEL["classes"], MODEL["relationships"])
    bad = verify_candidates(false_claim, MODEL["classes"], MODEL["relationships"])
    assert good[0]["verdict"] == "VERIFIED" and good[0]["evidence_refs"]
    assert bad[0]["verdict"] != "VERIFIED" and not bad[0]["evidence_refs"]


# 11. fake relationship -> INSUFFICIENT_EVIDENCE (unknown) / SUGGESTION (unrelated-known)
def test_fake_relationship_insufficient():
    out = verify_candidates(
        [{"severity": "HIGH", "title": "Ghost calls Phantom",
          "description": "Ghost calls Phantom and leaks data.",
          "file": "", "line_start": 0, "line_end": 0, "category": "Security"}],
        MODEL["classes"], MODEL["relationships"],
    )
    assert out[0]["verdict"] == "INSUFFICIENT_EVIDENCE"
    out2 = verify_candidates(
        [{"severity": "MEDIUM", "title": "OrderService calls PaymentGateway",
          "description": "OrderService calls PaymentGateway on checkout.",
          "file": "", "line_start": 0, "line_end": 0, "category": "Architecture"}],
        MODEL["classes"], MODEL["relationships"],
    )
    assert out2[0]["verdict"] == "AI_SUGGESTION"


# 12. centrality does not create VERIFIED finding
def test_centrality_is_not_proof():
    out = verify_candidates(
        [{"severity": "CRITICAL", "title": "OrderRepository is affected by this change",
          "description": "Central OrderRepository with many dependents must contain the bug.",
          "file": "", "line_start": 0, "line_end": 0, "category": "Architecture"}],
        MODEL["classes"], MODEL["relationships"],
    )
    assert out[0]["verdict"] != "VERIFIED"


# 13. base mismatch downgrades changed-line grounding (ReviewEngine level)
def test_base_mismatch_downgrade():
    from devlensx.evidence.resolver import register_snapshot
    from devlensx.chat.orchestrator import _model_store
    register_snapshot("shop", "run_base", "eval_repos/shop", "c0ffee")
    _model_store["run_base"] = MODEL
    try:
        from devlensx.review.review_engine import ReviewEngine
        diff = _diff("shop/OrderService.java", 40)
        exact = ReviewEngine.review(diff, "run_base", base_commit="c0ffee")
        assert exact["base_compat"]["status"] == EXACT_SNAPSHOT
        assert exact["what_changed"][0]["evidence_kind"] == "changed-line"
        skewed = ReviewEngine.review(diff, "run_base", base_commit="deadbeef")
        assert skewed["base_compat"]["status"] == BASE_MISMATCH
        assert skewed["what_changed"][0]["evidence_kind"] == "declaration"
        assert skewed["what_changed"][0]["changed_lines"] == [41]
    finally:
        _model_store.pop("run_base", None)


# 14. mermaid matches traversed graph only
def test_mermaid_matches_graph():
    diff = _diff("shop/OrderService.java", 40)
    changed = _changed(diff)
    aff = resolve_affected(changed, MODEL, SNAP, _FakeGraph({"placeOrder": ["OrderController"]}))
    mm = build_change_mermaid(changed, aff)
    assert mm.startswith("graph TD")
    allowed = {c.name for c in changed} | {a["target_symbol"] for a in aff} | \
              {a["source_symbol"] for a in aff}
    import re
    nodes = set(re.findall(r"(\w+)\[", mm))
    assert nodes <= {_mermaid_id(n) for n in allowed}

    # every edge connects a traversed pair
    pairs = {(a["source_symbol"], a["target_symbol"]) for a in aff}
    for line in mm.splitlines():
        m = re.match(r"\s*(\w+)\s*-->(?:\|([^|]*)\|)?\s*(\w+)", line)
        if m:
            src, _label, tgt = m.group(1), m.group(2), m.group(3)
            inv = {_mermaid_id(n): n for n in allowed}
            assert (inv[src], inv[tgt]) in pairs


def _mermaid_id(s):
    import re
    clean = re.sub(r"[^A-Za-z0-9_]", "_", str(s or ""))
    return ("n_" + clean) if clean and clean[0].isdigit() else (clean or "node")
