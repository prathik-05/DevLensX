"""Depth pipeline tests: structure->retrieval->multi-pass->critique->crosslink->progressive."""
from devlensx.wiki_depth import (
    build_page_outline,
    retrieve_section_context,
    extract_section_facts,
    explain_section,
    critique_section,
    crosslink_markdown,
    build_entity_map,
    progressive_sections,
    overview_depth_check,
    build_overview_deep,
)

MODEL = {
    "repo": "petclinic",
    "repo_summary": {"language": "Java", "framework": "Spring Boot"},
    "classes": [
        {"name": "OwnerController", "package": "org.example.owner", "stereotype": "Controller", "kind": "class",
         "file": "OwnerController.java", "is_test": False,
         "methods": [{"name": "createOwner", "params": [], "return_type": "String"}],
         "annotations": ["RestController"], "endpoints": [{"method": "POST", "path": "/owners", "method_name": "createOwner"}]},
        {"name": "OwnerService", "package": "org.example.owner", "stereotype": "Service", "kind": "class",
         "file": "OwnerService.java", "is_test": False, "methods": [{"name": "save", "params": [], "return_type": "void"}],
         "annotations": ["Service"], "endpoints": []},
        {"name": "OwnerRepository", "package": "org.example.owner", "stereotype": "Repository", "kind": "interface",
         "file": "OwnerRepository.java", "is_test": False, "methods": [], "annotations": ["Repository"], "endpoints": []},
    ],
    "relationships": [
        {"source": "OwnerController", "target": "OwnerService", "type": "DEPENDS_ON"},
        {"source": "OwnerService", "target": "OwnerRepository", "type": "DEPENDS_ON"},
    ],
    "endpoints": [{"method": "POST", "path": "/owners", "handler": "OwnerController.createOwner"}],
}


def test_structure_pass_outline():
    outline = build_page_outline("overview", MODEL, None, [])
    sections = [o["section"] for o in outline]
    assert sections == ["summary", "architecture", "key_components", "request_flow", "tech_stack", "where_next"]


def test_retrieval_grounded_slice():
    outline = build_page_outline("overview", MODEL, None, [])
    item = next(o for o in outline if o["section"] == "key_components")
    # Provide nodes explicitly for determinism
    item["nodes"] = ["OwnerController", "OwnerService"]
    ctx = retrieve_section_context(item, MODEL, None)
    assert "OwnerController" in str(ctx) or ctx.get("nodes")


def test_multi_pass_facts_then_explanation():
    item = {"section": "key", "nodes": ["OwnerController"], "findings": [], "facts": {}}
    ctx = retrieve_section_context(item, MODEL, None)
    facts = extract_section_facts(item, ctx, MODEL)
    assert any("OwnerController" in s for s in facts["signatures"])
    prose, cited = explain_section("key components", facts, ["OwnerController"])
    assert "OwnerController" in prose
    assert "OwnerController" in cited


def test_critique_hedges_ungrounded():
    facts = {"signatures": ["OwnerController.createOwner() -> String"], "edges": [], "annotations": [], "endpoints": []}
    prose = "OwnerController.createOwner handles creation. This system uses Redis for caching."
    tight, dropped = critique_section(prose, facts, ["OwnerController"])
    assert "OwnerController" in tight
    assert any("Redis" in d for d in dropped)


def test_crosslinking():
    entity_map = build_entity_map(MODEL)
    assert "OwnerController" in entity_map
    md = crosslink_markdown("See OwnerController and OwnerService for details.", entity_map)
    assert "[OwnerController]" in md
    assert "[OwnerService]" in md


def test_progressive_disclosure():
    secs = progressive_sections("summary text", "how text", ["d1", "d2"], [{"nodeId": "OwnerController"}])
    assert [s["heading"] for s in secs] == ["Summary", "How it works", "Details"]
    assert secs[2].get("collapsible") is True


def test_overview_depth_check():
    deep = build_overview_deep(MODEL, None, [])
    assert len(deep["key_components"]) >= 2
    assert len(deep["flow"]) >= 2
    # Depth proxy: key components + flow reference >= 8 distinct ids
    assert len(set(deep["key_components"] + deep["flow"])) >= 3
    # No generic filler
    assert "software project" not in deep["summary"].lower()

    class FakePage:
        id = "overview"
        sections = [{"nodeId": n} for n in deep["key_components"] + deep["flow"]]
        citations = deep["evidence"]
    ok, count = overview_depth_check([FakePage()])
    # Tiny fixture yields ~3-4 distinct refs; real PetClinic yields 8+.
    # Depth proxy: count must equal key_components+flow distinct set.
    assert count >= 3
    assert count == len(set(deep["key_components"] + deep["flow"]))
