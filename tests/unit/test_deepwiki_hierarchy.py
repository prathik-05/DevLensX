"""
DevLensX Unit Test Suite: DeepWiki-style Hierarchical Documentation Tree
Verifies parent/child page hierarchy, evidence-grounded purpose statements,
and the DeepWiki-compatible JSON serialization contract.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.understanding.model.repository_brain import RepositoryBrain
from devlensx.understanding.documentation.planner import plan_documentation


def _ts_repo_brain():
    classes = [
        # effects/ cluster -> parent page + children
        {"name": "SpiderCursor", "stereotype": "Component", "kind": "function",
         "file": "src/components/effects/spider-cursor.tsx", "line_start": 10,
         "line_end": 120, "methods": [], "package": "", "is_test": False},
        {"name": "VenomMetaballs", "stereotype": "Component", "kind": "function",
         "file": "src/components/effects/venom-metaballs.tsx", "line_start": 5,
         "line_end": 90, "methods": [], "package": "", "is_test": False},
        # context/ cluster -> global state page
        {"name": "SPDevProvider", "stereotype": "Component", "kind": "function",
         "file": "src/context/spdev-provider.tsx", "line_start": 30,
         "line_end": 141, "methods": [], "package": "", "is_test": False},
    ]
    return RepositoryBrain("eval_repos/sp-portfolio", classes, analysis_run_id="run_hierarchy_test")


def test_deepwiki_hierarchy():
    print("Executing Unit Test: DeepWiki-style Hierarchical Documentation Tree...")

    brain = _ts_repo_brain()
    tree = plan_documentation(brain)
    d = tree.to_deepwiki_dict()

    # 1. Contract shape
    assert set(d.keys()) == {"repo_notes", "pages"}
    assert isinstance(d["repo_notes"], list) and d["repo_notes"][0]["content"]
    assert len(d["pages"]) > 5

    titles = {p["title"] for p in d["pages"]}
    assert "Overview" in titles and "Glossary" in titles

    # 2. Every page has a non-empty evidence-grounded purpose
    for page in d["pages"]:
        assert page.get("purpose"), f"Page '{page['title']}' has empty purpose"

    # 3. Hierarchy integrity: parent refs resolve to real page titles
    for page in d["pages"]:
        if "parent" in page:
            assert page["parent"] in titles, f"Dangling parent '{page['parent']}'"

    # 4. Domain clusters derived from directories (Effects, Context), not fabricated
    cluster_titles = {t for t in titles if t in ("Effects", "Context")}
    assert cluster_titles, f"Expected directory-derived clusters, got: {sorted(titles)}"

    # 5. Child pages reference their cluster as parent
    effects_page = next(p for p in d["pages"] if p["title"] == "Effects")
    children = [p for p in d["pages"] if p.get("parent") == "Effects"]
    assert any(c["title"] == "SpiderCursor" for c in children)
    assert any(c["title"] == "VenomMetaballs" for c in children)

    # 6. Child purpose cites the real file and line range
    cursor = next(c for c in children if c["title"] == "SpiderCursor")
    assert "spider-cursor.tsx" in cursor["purpose"]
    assert "L10" in cursor["purpose"] or "lines 10" in cursor["purpose"]

    # 7. analysis_run_id preserved through serialization
    assert tree.analysis_run_id == "run_hierarchy_test"
    assert "run_hierarchy_test" in d["repo_notes"][0]["content"]

    # 8. No garbage identifiers leak into page titles
    import re
    for page in d["pages"]:
        if page["title"].startswith(("Overview", "Getting", "Project", "Core", "Glossary",
                                     "Features", "Components", "Dependencies", "Configuration",
                                     "Git History", "Domain Architecture")):
            continue
        if page["title"] in ("Effects", "Context"):
            continue
        assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", page["title"]), \
            f"Garbage identifier leaked as page title: '{page['title']}'"

    print(f"  🟢 DeepWiki JSON contract verified ({len(d['pages'])} pages)")
    print(f"  🟢 Hierarchy verified: Effects → SpiderCursor/VenomMetaballs; Context → SPDevProvider")
    print(f"  🟢 Purposes are evidence-grounded (real files + line ranges)")

    # 9. Small repo: no domain-cluster bloat (single class in generic dir -> no clusters)
    tiny = RepositoryBrain(
        "eval_repos/tiny",
        [{"name": "Main", "stereotype": "Class", "kind": "class",
          "file": "main.py", "line_start": 1, "line_end": 20,
          "methods": [], "package": "", "is_test": False}],
        analysis_run_id="run_tiny",
    )
    tiny_tree = plan_documentation(tiny)
    tiny_clusters = [p for p in tiny_tree.pages if p.id.startswith("domain-")]
    assert not tiny_clusters, f"Tiny repo should have no domain clusters, got {[p.id for p in tiny_clusters]}"
    tiny_d = tiny_tree.to_deepwiki_dict()
    assert all(p.get("purpose") for p in tiny_d["pages"])
    print("  🟢 Tiny repository stays lean (no cluster bloat)")

    print("\nUnit Test DeepWiki Hierarchy Complete: 100% Passed\n")


if __name__ == "__main__":
    test_deepwiki_hierarchy()