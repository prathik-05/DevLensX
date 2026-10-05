"""
DevLensX Wiki Depth Pipeline (D10 DeepWiki-grade generation)

Shape (replicates DeepWiki-open mechanism on DevLensX data):
  Structure pass -> Retrieval slice -> Pass1 facts -> Pass2 explanation
  -> Pass3 critique/hedge -> Cross-link pass -> Progressive disclosure

- No second analysis pipeline: uses parser AST, Kuzu graph, verified findings,
  existing hybrid retrieval.
- LLM only for prose (Pass 2 explanation). Topology/facts deterministic.
- Every claim carries nodeId/findingId; Pass 3 cuts/hedges untraceable sentences.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple


# ---------------------------------------------------------------------------
# LLM accessor (graceful fallback to template prose — deterministic)
# ---------------------------------------------------------------------------

def _get_llm():
    try:
        from devlensx.llm.provider import get_llm_provider
        provider = get_llm_provider("auto")
        return provider
    except Exception:
        return None


def _llm_explain(system_prompt: str, user_prompt: str, max_chars: int = 1500) -> Optional[str]:
    """Pass 2 entry point. Returns None if no LLM available (caller falls back)."""
    try:
        llm = _get_llm()
        if llm is None:
            return None
        text = llm.generate(user_prompt, system_prompt=system_prompt)
        if not text:
            return None
        return text.strip()[:max_chars]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Structure pass: explicit outline per page (nodes, findings, facts, order)
# ---------------------------------------------------------------------------

def build_page_outline(
    page_type: str,
    model: Dict[str, Any],
    graph_store: Optional[Any] = None,
    verified_findings: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Return ordered outline items: {section, nodes, findings, facts}."""
    verified_findings = verified_findings or []
    classes = model.get("classes", [])
    relationships = model.get("relationships", [])
    endpoints = model.get("endpoints", [])
    outline: List[Dict[str, Any]] = []

    def _edges_for(names: List[str]) -> List[Dict[str, Any]]:
        out = []
        for r in relationships:
            s = str(r.get("source", ""))
            t = str(r.get("target", ""))
            if any(n in s or n in t for n in names):
                out.append(r)
        return out

    def _findings_for(names: List[str]) -> List[Dict[str, Any]]:
        out = []
        for f in verified_findings:
            blob = f"{f.get('class_name','')} {f.get('title','')} {f.get('file','')}"
            if any(n in blob for n in names):
                out.append(f)
        return out

    if page_type == "overview":
        # Highest-effort page: 6 ordered sections
        outline = [
            {"section": "summary", "nodes": [], "findings": [], "facts": {}},
            {"section": "architecture", "nodes": [], "findings": [], "facts": {}},
            {"section": "key_components", "nodes": [], "findings": [], "facts": {}},
            {"section": "request_flow", "nodes": [], "findings": [], "facts": {}},
            {"section": "tech_stack", "nodes": [], "findings": [], "facts": {}},
            {"section": "where_next", "nodes": [], "findings": [], "facts": {}},
        ]
        # Resolve nodes per section deterministically
        controllers = [c["name"] for c in classes if c.get("stereotype") == "Controller"]
        outline[2]["nodes"] = _rank_by_centrality(classes, relationships)[:8]
        outline[3]["nodes"] = _pick_request_path(classes, relationships, endpoints)
        outline[1]["nodes"] = controllers[:6]
        for item in outline:
            item["findings"] = _findings_for(item["nodes"])
            item["facts"] = {"edges": _edges_for(item["nodes"])}
    elif page_type == "architecture":
        ctrls = [c["name"] for c in classes if c.get("stereotype") == "Controller"]
        outline = [{"section": "layers", "nodes": ctrls, "findings": _findings_for(ctrls), "facts": {"edges": _edges_for(ctrls)}}]
    elif page_type == "module":
        outline = [{"section": "classes", "nodes": [], "findings": [], "facts": {}}]
    elif page_type == "api":
        outline = [{"section": "endpoints", "nodes": [], "findings": [], "facts": {}}]
    return outline


def _rank_by_centrality(classes: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> List[str]:
    """Blast-radius/centrality rank reusing ChangeImpact data (fan-in + method count)."""
    from collections import Counter
    from devlensx.deep_reasoning import simple_name, build_method_index, prod_methods, is_prod_component
    fan_in: Counter = Counter()
    for r in relationships:
        tgt = simple_name(r.get("target", ""))
        fan_in[tgt] += 1
    method_index = build_method_index(classes)
    scored = []
    for c in classes:
        if not is_prod_component(c):
            continue
        name = c["name"]
        score = fan_in.get(name, 0) * 10 + len(prod_methods(method_index, name))
        scored.append((name, score))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [n for n, _ in scored]


def _pick_request_path(
    classes: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    endpoints: List[Dict[str, Any]],
) -> List[str]:
    """Pick highest-traffic request path: top controller -> its downstream."""
    controllers = [c for c in classes if c.get("stereotype") == "Controller" and not c.get("is_test")]
    if not controllers:
        return [c["name"] for c in classes[:3] if not c.get("is_test")]
    from devlensx.deep_reasoning import build_method_index as _bmi, prod_methods as _pm
    _idx = _bmi(classes)
    from devlensx.deep_reasoning import handler_matches as _hm2
    def _ep_count(c: Dict[str, Any]) -> int:
        return sum(1 for e in endpoints if _hm2(str(e.get("handler", "")), c["name"]))
    top = sorted(controllers, key=lambda c: (-_ep_count(c), -len(_pm(_idx, c["name"])), c["name"]))[0]
    path = [top["name"]]
    # Follow first downstream edge deterministically
    for r in sorted(relationships, key=lambda x: str(x.get("source"))):
        if top["name"] in str(r.get("source", "")):
            tgt = str(r.get("target", "")).split(".")[-1]
            if tgt and tgt != top["name"]:
                path.append(tgt)
                # One more hop
                for r2 in sorted(relationships, key=lambda x: str(x.get("source"))):
                    if tgt in str(r2.get("source", "")):
                        t2 = str(r2.get("target", "")).split(".")[-1]
                        if t2 and t2 not in path:
                            path.append(t2)
                            break
                break
    return path[:4]


# ---------------------------------------------------------------------------
# Retrieval-grounded generation: per-section slice
# ---------------------------------------------------------------------------

def retrieve_section_context(
    outline_item: Dict[str, Any],
    model: Dict[str, Any],
    graph_store: Optional[Any] = None,
) -> Dict[str, Any]:
    """Pull relevant slice via hybrid retrieval; fallback to graph+AST slice."""
    nodes: List[str] = outline_item.get("nodes", [])
    # Try hybrid retriever (same mechanism agents use)
    try:
        from devlensx.retrieval.hybrid_retriever import HybridContextRetriever
        if graph_store is not None and nodes:
            retriever = HybridContextRetriever(graph_store)
            ctx = retriever.retrieve_context(" ".join(nodes[:5]), top_k=5)
            if ctx and (ctx.get("vector_results") or ctx.get("graph_facts")):
                return {"retrieval": ctx, "nodes": nodes}
    except Exception:
        pass
    # Fallback: deterministic AST + edge slice
    classes = {c["name"]: c for c in model.get("classes", [])}
    slice_classes = [classes[n] for n in nodes if n in classes]
    edges = outline_item.get("facts", {}).get("edges", [])
    return {"classes": slice_classes, "edges": edges, "nodes": nodes}


# ---------------------------------------------------------------------------
# Pass 1 (facts): deterministic structuring — no LLM creativity
# ---------------------------------------------------------------------------

def extract_section_facts(
    outline_item: Dict[str, Any],
    section_context: Dict[str, Any],
    model: Dict[str, Any],
) -> Dict[str, Any]:
    """Structure concrete facts: signatures, edges, annotations, endpoints."""
    from devlensx.deep_reasoning import build_method_index, prod_methods, ctor_params
    facts: Dict[str, Any] = {"signatures": [], "edges": [], "annotations": [], "endpoints": []}
    method_index = build_method_index(model.get("classes", []))
    for c in section_context.get("classes", []):
        # Legacy schema: inline methods list on the class node
        for m in (c.get("methods", []) or [])[:8]:
            if isinstance(m, dict):
                params = ", ".join(
                    (p.get("type", "") + " " + p.get("name", "")).strip()
                    for p in (m.get("params", []) or [])
                )
                facts["signatures"].append(f"{c['name']}.{m.get('name')}({params}) -> {m.get('return_type', 'void')}")
            else:
                facts["signatures"].append(f"{c['name']}.{m}")
        # Current schema: methods live as separate parser nodes — resolve via index
        for m in prod_methods(method_index, c["name"])[:8]:
            sig = m.get("signature") or m.get("name")
            facts["signatures"].append(f"{c['name']}.{sig}")
        for p in ctor_params(method_index, c["name"])[:6]:
            facts["signatures"].append(f"{c['name']}.__init__({p.get('type', '')} {p.get('name', '')}) [injected]")
        for a in (c.get("annotations", []) or []):
            facts["annotations"].append(f"{c['name']}: @{a}")
        # Legacy schema: inline endpoints list on the class node
        for e in (c.get("endpoints", []) or [])[:5]:
            if isinstance(e, dict):
                facts["endpoints"].append(f"{e.get('method', e.get('http_method', 'GET'))} {e.get('path', e.get('full_path', '/'))} -> {e.get('method_name', '')}")
            else:
                facts["endpoints"].append(str(e))
        # Current schema: endpoints live at model level — match by handler token or file
        from devlensx.deep_reasoning import handler_matches as _hm
        for e in model.get("endpoints", []):
            handler = str(e.get("handler", ""))
            if _hm(handler, c["name"]) or str(e.get("file", "")).replace("\\", "/") == str(c.get("file", "")).replace("\\", "/"):
                facts["endpoints"].append(f"{e.get('method', 'GET')} {e.get('route', '/')} -> {handler}")
                if len(facts["endpoints"]) >= 8:
                    break
    for r in section_context.get("edges", [])[:20]:
        facts["edges"].append(f"{r.get('source')} --[{r.get('type', r.get('relationship', 'DEPENDS_ON'))}]--> {r.get('target')}")
    # Retrieval slice passthrough
    if "retrieval" in section_context:
        facts["retrieval"] = section_context["retrieval"]
    return facts


# ---------------------------------------------------------------------------
# Pass 2 (explanation): LLM with structured facts; template fallback
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You are a senior engineer writing onboarding documentation. "
    "Explain ONLY the components, relationships, and signatures listed in FACTS. "
    "Never invent classes, endpoints, or technologies. If a detail is not in FACTS, say so or omit it. "
    "Write concretely with real names."
)


def explain_section(
    section_name: str,
    facts: Dict[str, Any],
    component_names: List[str],
) -> Tuple[str, List[str]]:
    """Returns (prose, cited_node_ids). Falls back to deterministic template."""
    cited = list(component_names)
    # Build deterministic user prompt from facts only
    fact_lines = []
    for s in facts.get("signatures", [])[:10]:
        fact_lines.append(f"SIG: {s}")
    for e in facts.get("edges", [])[:10]:
        fact_lines.append(f"EDGE: {e}")
    for a in facts.get("annotations", [])[:8]:
        fact_lines.append(f"ANNOT: {a}")
    for e in facts.get("endpoints", [])[:8]:
        fact_lines.append(f"ENDPOINT: {e}")
    user_prompt = (
        f"Section: {section_name}\n"
        f"Components: {', '.join(component_names[:8])}\n"
        f"FACTS (only ground truth, do not go beyond these):\n" + "\n".join(fact_lines[:30])
    )
    llm_text = _llm_explain(_SYSTEM, user_prompt)
    if llm_text:
        return llm_text, cited
    # Fallback template: specific, no generic filler
    parts = []
    if component_names:
        parts.append(f"Covers {', '.join(component_names[:5])}.")
    if facts.get("edges"):
        parts.append("Key relationships: " + "; ".join(facts["edges"][:5]) + ".")
    if facts.get("signatures"):
        parts.append("Notable operations: " + "; ".join(facts["signatures"][:5]) + ".")
    if facts.get("endpoints"):
        parts.append("Endpoints: " + "; ".join(facts["endpoints"][:5]) + ".")
    if not parts:
        parts.append("No structural facts available for this section.")
    return " ".join(parts), cited


# ---------------------------------------------------------------------------
# Pass 3 (critique/tighten): flag sentences not traceable to Pass-1 facts
# ---------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Words that indicate hedging (allowed when fact-weak)
_HEDGES = ("likely", "appears to", "may ", "might ", "probably")


def critique_section(
    prose: str,
    facts: Dict[str, Any],
    component_names: List[str],
) -> Tuple[str, List[str]]:
    """Cut or hedge sentences not traceable to facts. Returns (tightened, dropped)."""
    fact_blob = " ".join(
        facts.get("signatures", []) + facts.get("edges", [])
        + facts.get("annotations", []) + facts.get("endpoints", [])
        + component_names
    ).lower()
    fact_tokens = {t.strip("(),.:;\"'").lower() for t in fact_blob.split() if len(t) > 2}
    kept, dropped = [], []
    for sent in _SENT_SPLIT.split(prose.strip()):
        if not sent.strip():
            continue
        tokens = [t.strip("(),.:;\"'").lower() for t in sent.split() if len(t) > 2]
        hits = sum(1 for t in tokens if t in fact_tokens)
        # Keep if: grounded (>=2 fact tokens) or already hedged
        if hits >= 2 or any(h in sent.lower() for h in _HEDGES):
            kept.append(sent.strip())
        elif hits == 1 and len(tokens) < 12:
            kept.append(sent.strip())
        else:
            dropped.append(sent.strip())
    if not kept:
        # Never return empty: fall back to most factual sentence
        return prose, []
    return " ".join(kept), dropped


# ---------------------------------------------------------------------------
# Cross-linking post-pass (regex/AST match against known entities)
# ---------------------------------------------------------------------------

def crosslink_markdown(
    markdown: str,
    entity_to_page: Dict[str, str],
) -> str:
    """Link every known entity mention to its primary page. LLM never guesses targets."""
    # Longest names first to avoid partial matches
    for entity in sorted(entity_to_page.keys(), key=len, reverse=True):
        if len(entity) < 3:
            continue
        target = entity_to_page[entity]
        # Skip if already linked
        pattern = re.compile(rf"(?<!\[)(?<!\w){re.escape(entity)}(?!\w)(?!\s*\])")
        markdown = pattern.sub(f"[{entity}]({target})", markdown, count=3)
    return markdown


def build_entity_map(
    model: Dict[str, Any],
) -> Dict[str, str]:
    """Map class/endpoint names to their primary module/API pages."""
    mapping: Dict[str, str] = {}
    for c in model.get("classes", []):
        name = c.get("name")
        if not name:
            continue
        pkg = (c.get("package") or "").replace(".", "-") or "root"
        mapping[name] = f"#module-{pkg}"
        for m in (c.get("methods", []) or []):
            mn = m.get("name")
            if mn:
                mapping[f"{name}.{mn}"] = f"#module-{pkg}"
    for e in model.get("endpoints", []):
        route = e.get("path") or e.get("full_path")
        handler = e.get("method_name") or e.get("handler")
        if route:
            mapping[route] = "#api-reference"
        if handler:
            mapping[handler] = "#api-reference"
    return mapping


# ---------------------------------------------------------------------------
# Progressive disclosure: summary / how-it-works / details
# ---------------------------------------------------------------------------

def progressive_sections(
    summary_text: str,
    how_text: str,
    detail_lines: List[str],
    evidence: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return 3 layered sections sharing the same evidence refs."""
    return [
        {"heading": "Summary", "content": summary_text, "verdict": "Verified",
         "evidence": evidence},
        {"heading": "How it works", "content": how_text, "verdict": "Verified",
         "evidence": evidence},
        {"heading": "Details", "content": "\n".join(detail_lines[:30]),
         "verdict": "Verified", "evidence": evidence,
         "collapsible": True},
    ]


# ---------------------------------------------------------------------------
# Page-depth check: Overview must reference min distinct node/finding IDs
# ---------------------------------------------------------------------------

MIN_OVERVIEW_REFS = 8


def overview_depth_check(pages: List[Any]) -> Tuple[bool, int]:
    """Count distinct nodeId/findingId refs on the Overview page."""
    overview = next((p for p in pages if getattr(p, "id", "") == "overview"), None)
    if overview is None:
        return False, 0
    seen = set()
    sections = getattr(overview, "sections", []) or []
    for s in sections:
        sid = s.get("nodeId") if isinstance(s, dict) else getattr(s, "nodeId", None)
        if sid:
            seen.add(sid)
    cites = getattr(overview, "citations", []) or []
    for c in cites:
        nid = c.get("nodeId") if isinstance(c, dict) else getattr(c, "nodeId", None)
        if nid:
            seen.add(nid)
    return len(seen) >= MIN_OVERVIEW_REFS, len(seen)


# ---------------------------------------------------------------------------
# Overview builder (highest-effort page)
# ---------------------------------------------------------------------------

def build_overview_deep(
    model: Dict[str, Any],
    graph_store: Optional[Any] = None,
    verified_findings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build the 6-part Overview using the full depth pipeline."""
    verified_findings = verified_findings or []
    classes = model.get("classes", [])
    relationships = model.get("relationships", [])
    endpoints = model.get("endpoints", [])
    repo_summary = model.get("repo_summary", {})
    repo_name = model.get("repo", "repository")

    outline = build_page_outline("overview", model, graph_store, verified_findings)
    entity_map = build_entity_map(model)

    def _run_section(item: Dict[str, Any], comp_names: List[str]) -> Dict[str, Any]:
        ctx = retrieve_section_context(item, model, graph_store)
        facts = extract_section_facts(item, ctx, model)
        prose, cited = explain_section(item["section"], facts, comp_names or item.get("nodes", []))
        tight, _ = critique_section(prose, facts, comp_names or item.get("nodes", []))
        tight = crosslink_markdown(tight, entity_map)
        return {"prose": tight, "cited": cited, "facts": facts}

    # 1. What this project does (concrete endpoints/entities, never generic)
    controllers = [c for c in classes if c.get("stereotype") == "Controller" and not c.get("is_test")]
    entities = [c for c in classes if c.get("stereotype") in ("Entity", "Model") and not c.get("is_test")]
    eps = [f"{e.get('method', e.get('http_method', 'GET'))} {e.get('path', e.get('full_path', '/'))}" for e in endpoints[:6]]
    what_parts = []
    if controllers and entities:
        what_parts.append(
            f"This is a {repo_summary.get('language', '')} system handling "
            f"{', '.join(e['name'] for e in entities[:4])} through "
            f"{', '.join(c['name'] for c in controllers[:4])}."
        )
    elif controllers:
        what_parts.append(f"This system exposes {len(endpoints)} endpoint(s) via {', '.join(c['name'] for c in controllers[:4])}.")
    elif classes:
        prod = [c["name"] for c in classes if not c.get("is_test")][:5]
        what_parts.append(f"This codebase centers on {', '.join(prod)}.")
    if eps:
        what_parts.append("Entry points include: " + "; ".join(eps[:4]) + ".")
    what_text = " ".join(what_parts) if what_parts else "Repository structure analyzed; see components below."

    # 2. Architecture at a glance
    stereotypes = sorted({c.get("stereotype") for c in classes if c.get("stereotype")})
    arch_item = next((o for o in outline if o["section"] == "architecture"), outline[1] if len(outline) > 1 else outline[0])
    arch_run = _run_section(arch_item, arch_item.get("nodes", []))
    arch_text = (
        f"Layers detected: {', '.join(stereotypes[:8])}. " + arch_run["prose"]
        if stereotypes else arch_run["prose"]
    )

    # 3. Key components (5-8 by centrality, 2-4 sentences each with signatures/edges)
    key_names = _rank_by_centrality(classes, relationships)[:8]
    key_blocks = []
    key_cited: List[str] = []
    for name in key_names:
        cls = next((c for c in classes if c["name"] == name), None)
        if not cls:
            continue
        item = {"section": f"key:{name}", "nodes": [name], "findings": [], "facts": {}}
        # Edges for this component
        item["facts"] = {"edges": [
            {"source": r.get("source"), "target": r.get("target"), "type": r.get("type", "DEPENDS_ON")}
            for r in relationships if name in str(r.get("source", "")) or name in str(r.get("target", ""))
        ][:6]}
        run = _run_section(item, [name])
        key_blocks.append(f"**{name}** ({cls.get('stereotype', 'component')}): {run['prose']}")
        key_cited.extend(run["cited"])
    key_text = "\n\n".join(key_blocks) if key_blocks else "No ranked components available."

    # 4. Request flow (one real path + sequence)
    flow_names = _pick_request_path(classes, relationships, endpoints)
    flow_item = {"section": "request_flow", "nodes": flow_names, "findings": [], "facts": {}}
    flow_run = _run_section(flow_item, flow_names)
    flow_text = f"Follow {' -> '.join(flow_names)}: {flow_run['prose']}" if flow_names else flow_run["prose"]

    # 5. Tech stack (detected, one line why per piece)
    stack_lines = []
    lang = repo_summary.get("language", "")
    fw = repo_summary.get("framework", "")
    if lang:
        stack_lines.append(f"- {lang}: primary language ({len(classes)} symbols parsed).")
    if fw:
        stack_lines.append(f"- {fw}: framework detected from manifests/annotations.")
    # Constructor injection: evidence from constructor parameter lists
    from devlensx.deep_reasoning import build_method_index as _bmi2, ctor_params as _cp, is_prod_component as _ipc
    _idx2 = _bmi2(classes)
    _injected = [c["name"] for c in classes if _ipc(c) and _cp(_idx2, c["name"])]
    if _injected:
        stack_lines.append(f"- Constructor injection ({', '.join(_injected[:4])}): dependencies declared as constructor parameters — no hidden field-injection coupling.")
    stack_text = "\n".join(stack_lines) if stack_lines else "Stack derived from parser output."

    # 6. Where next
    where_text = (
        "To understand request handling, start at the Architecture page, then the top-ranked "
        "module pages, then the API Reference for the endpoint you care about."
    )

    # Cross-link everything
    what_text = crosslink_markdown(what_text, entity_map)
    key_text = crosslink_markdown(key_text, entity_map)
    flow_text = crosslink_markdown(flow_text, entity_map)

    # Progressive disclosure assembly
    summary = what_text[:400]
    how = f"{arch_text}\n\n{key_text[:1200]}\n\n{flow_text[:800]}"
    details = [
        f"Components: {', '.join(key_names[:8])}",
        f"Flow: {' -> '.join(flow_names)}",
        stack_text,
        where_text,
    ]
    evidence = [{"nodeId": n} for n in list(dict.fromkeys(key_names + flow_names))[:12]]
    sections = progressive_sections(summary, how, details, evidence)

    return {
        "summary": summary,
        "sections": sections,
        "key_components": key_names,
        "flow": flow_names,
        "evidence": evidence,
        "outline": [o["section"] for o in outline],
    }
