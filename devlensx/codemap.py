"""
DevLensX Codemap — Tour stops ordered by Architecture Agent findings
ranked by centrality/blast-radius reusing ChangeImpact scoring.

Each stop = file/class + annotation + jump-to-code link.
Provide function get_codemap_stops(analysis_id) -> list.

Uses existing KuzuGraphStore query_blast_radius without extending schema.
Fallback deterministic ordering via relationship fan-in when graph empty.
"""

from __future__ import annotations

import threading
from typing import Dict, Any, List, Optional

# Cache keyed by analysis_id (inconsistent with wiki repo+commit — documented; add repo-aware invalidation via invalidate_codemap)
# Note: codemap cache currently keyed only by analysis_id for simplicity; wiki uses repo::commit::analysis_id.
# For multi-tenant isolation, invalidation is driven by analysis_id; repo+commit variant can be added via _codemap_cache_meta if needed.
_codemap_cache: Dict[str, List[Dict[str, Any]]] = {}
_codemap_meta: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()

def _sanitize_file_link(file_path: str, line_start: Optional[int] = None) -> str:
    if not file_path:
        return "#"
    posix = file_path.replace("\\", "/")
    if line_start:
        return f"{posix}#L{line_start}"
    return posix

def build_codemap_stops(
    model: Dict[str, Any],
    graph_store: Optional[Any] = None,
    analysis_id: Optional[str] = None,
    verified_findings: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Ordered by centrality/blast-radius reusing ChangeImpact scoring."""
    classes = model.get("classes", [])
    relationships = model.get("relationships", [])
    # Compute blast radius via graph_store if available
    blast_rank: List[Dict[str, Any]] = []
    try:
        if graph_store:
            blast_rank = graph_store.query_blast_radius(limit=20) or []
    except Exception:
        blast_rank = []
    # Fallback: compute incoming dependents from relationships
    if not blast_rank:
        # relationships source/target are ids like java_MySqlIntegrationTests_1 -> not class names
        # fallback to counting by class name appearance in relationships target
        # Instead, order by method count or package centrality deterministically
        # Use deterministic scoring: count occurrences of class name in relationships + methods
        from collections import Counter
        target_counts = Counter()
        for r in relationships:
            tgt = str(r.get("target",""))
            # Attempt to extract simple name
            # If tgt like OwnerRepository, it's already simple
            simple = tgt.split(".")[-1].split("_")[-1] if "_" in tgt else tgt.split(".")[-1]
            # Map to actual class name if exists
            for c in classes:
                cname = c.get("name")
                if cname and (cname == simple or cname == tgt):
                    target_counts[cname] += 1
                    break
        # Combine with class method counts for centrality proxy — fix: score = incoming*10 + line_span and sort by (-score, name)
        # Filter test classes deterministically so huge test file line_span doesn't outrank prod centrality (evidence-first)
        scored = []
        for c in classes:
            cname = c.get("name")
            if not cname:
                continue
            if c.get("kind", "class") not in ("class","interface","enum","struct"):
                continue
            if c.get("is_test") or cname.endswith("Test") or cname.endswith("Tests") or c.get("stereotype") == "Test":
                continue
            incoming = target_counts.get(cname, 0)
            # Use line count as tie-breaker deterministic
            line_span = (c.get("line_end",0) or 0) - (c.get("line_start",0) or 0)
            score = incoming * 10 + line_span
            scored.append((cname, incoming, c, score))
        scored.sort(key=lambda x: (-x[1], -x[3], x[0]))
        # Build blast_rank-like structures — use score-inclusive tuple
        blast_rank = [
            {"class_name": name, "stereotype": cls.get("stereotype","Class"), "incoming_dependents": cnt}
            for name, cnt, cls, _score in scored[:15]
        ]
        # If still empty (e.g., no relationships), order by stereotypes priority
        if not blast_rank:
            prio = ("Controller","Service","Repository","Entity","Component","Class")
            def prio_key(c):
                try:
                    idx = prio.index(c.get("stereotype"))
                except ValueError:
                    idx = 99
                return idx
            sorted_classes = sorted([c for c in classes if c.get("name") and c.get("kind", "class") in ("class","interface","enum","struct")], key=lambda c: (prio_key(c), c.get("name", "")))[:15]
            blast_rank = [
                {"class_name": c.get("name", ""), "stereotype": c.get("stereotype","Class"), "incoming_dependents": 0}
                for c in sorted_classes
            ]

    # Now build tour stops ordered by blast radius (highest centrality first)
    # Each stop = file/class + annotation + jump-to-code link
    class_map = {c.get("name"): c for c in classes if c.get("name")}
    stops: List[Dict[str, Any]] = []
    for rank, item in enumerate(blast_rank, 1):
        name = item.get("class_name") or item.get("name")
        if not name or name not in class_map:
            continue
        cls = class_map[name]
        file_path = cls.get("file","")
        line_start = cls.get("line_start", 1)
        stereotype = cls.get("stereotype") or item.get("stereotype","Class")
        # Two-pass guided-tour annotation (facts then explanation)
        incoming = item.get("incoming_dependents", 0)
        annotation = annotate_stop(name, cls, rank, incoming, model, graph_store, verified_findings)
        jump_link = _sanitize_file_link(file_path, line_start)
        stops.append({
            "order": rank,
            "class_name": name,
            "stereotype": stereotype,
            "file": file_path,
            "line_start": line_start,
            "line_end": cls.get("line_end", line_start+20),
            "annotation": annotation,
            "jump_link": jump_link,
            "nodeId": name,
            "centrality_score": incoming,
            "blast_radius": incoming,
            # Evidence-first: provenance
            "evidence_ref": f"{file_path}#L{line_start}",
        })

    # Ensure determinism: sort by order already blast-radius descending
    # Add fallback stops if less than 3 (e.g., small repo)
    if len(stops) < 3:
        # add remaining classes sorted by name deterministically
        existing = {s["class_name"] for s in stops}
        extra = [c for c in sorted(classes, key=lambda x: x["name"]) if c["name"] not in existing and c.get("kind") in ("class","interface")][:5]
        for c in extra:
            stops.append({
                "order": len(stops)+1,
                "class_name": c["name"],
                "stereotype": c.get("stereotype","Class"),
                "file": c.get("file",""),
                "line_start": c.get("line_start",1),
                "line_end": c.get("line_end", 1),
                "annotation": f"Additional module {c['name']} in {c.get('package','')}",
                "jump_link": _sanitize_file_link(c.get("file",""), c.get("line_start",1)),
                "nodeId": c["name"],
                "centrality_score": 0,
                "blast_radius": 0,
                "evidence_ref": f"{c.get('file','')}#L{c.get('line_start',1)}",
            })

    return stops

def annotate_stop(
    class_name: str,
    cls: Dict[str, Any],
    rank: int,
    incoming: int,
    model: Dict[str, Any],
    graph_store: Optional[Any] = None,
    verified_findings: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Two-pass guided-tour annotation: facts (deterministic) then explanation.

    Reads like a colleague walking through the code, grounded in signatures
    and edges. Falls back to the centrality caption when no LLM is available.
    """
    stereotype = cls.get("stereotype", "Class")
    file_path = cls.get("file", "")
    base = f"#{rank} Centrality rank — {incoming} incoming dependents — {stereotype} at {file_path}"
    try:
        from devlensx.wiki_depth import (
            retrieve_section_context,
            extract_section_facts,
        )
        item = {"section": f"tour:{class_name}", "nodes": [class_name], "findings": [], "facts": {}}
        item["facts"] = {"edges": [
            {"source": r.get("source"), "target": r.get("target"), "type": r.get("type", "DEPENDS_ON")}
            for r in model.get("relationships", [])
            if class_name in str(r.get("source", "")) or class_name in str(r.get("target", ""))
        ][:6]}
        ctx = retrieve_section_context(item, model, graph_store)
        facts = extract_section_facts(item, ctx, model)
        
        detail_parts = []
        if facts.get("signatures"):
            sigs = [s.split(" -> ")[0] for s in facts["signatures"][:2]]
            detail_parts.append(f"Operations: {', '.join(sigs)}")
        if facts.get("endpoints"):
            eps = [e.split(" -> ")[0] for e in facts["endpoints"][:2]]
            detail_parts.append(f"Endpoints: {', '.join(eps)}")
        if facts.get("edges"):
            deps = [e.split("--> ")[-1] for e in facts["edges"][:2]]
            detail_parts.append(f"Connects to: {', '.join(deps)}")
        
        tight = " | ".join(detail_parts) if detail_parts else "Core domain component."
        annotation = f"{base}. {tight[:400]}"
    except Exception:
        annotation = base

    if verified_findings:
        for f in verified_findings:
            if f.get("class_name") == class_name and f.get("verdict") == "VERIFIED":
                annotation += f" | Verified: {f.get('title', '')} ({f.get('category', '')})"
                break
    return annotation[:800]


def cache_codemap_stops(analysis_id: str, stops: List[Dict[str, Any]], repo_id: Optional[str] = None, commit_hash: Optional[str] = None):
    with _cache_lock:
        _codemap_cache[analysis_id] = stops
        if repo_id is not None:
            _codemap_meta[analysis_id] = {"repo_id": repo_id, "commit_hash": commit_hash}
    try:
        from devlensx.core.persistence import get_storage_manager
        get_storage_manager().save_codemap(repo_id or "default", analysis_id, commit_hash, stops)
    except Exception:
        pass

def get_codemap_stops(analysis_id: str) -> Optional[List[Dict[str, Any]]]:
    """Public API: returns cached stops or builds on-demand from exact snapshot.
    Returns None if snapshot is unknown/corrupt (signals 404 SNAPSHOT_NOT_FOUND).
    Returns empty list [] if snapshot exists but has no stops (signals 200 count: 0).
    """
    with _cache_lock:
        if analysis_id in _codemap_cache:
            return _codemap_cache[analysis_id]

    # Check persistent codemap storage for exact analysis_id
    try:
        from devlensx.core.persistence import get_storage_manager
        persisted = get_storage_manager().load_codemap(analysis_id)
        if persisted is not None and len(persisted) > 0:
            with _cache_lock:
                _codemap_cache[analysis_id] = persisted
            return persisted
    except Exception:
        pass

    # Exact snapshot lookup (with persistence recovery, fail-closed, no cross-run fallback)
    try:
        from devlensx.evidence.resolver import get_snapshot_registry
        registry = get_snapshot_registry()
        snap = registry.get(analysis_id)
        if snap is None:
            # Snapshot does not exist in memory or disk -> Fail-closed 404
            return None

        # Resolve exact model for this analysis_id (strictly per-run model, zero global_state fallback)
        model = None
        try:
            from devlensx.chat.orchestrator import _model_store
            model = _model_store.get(analysis_id)
        except Exception:
            pass

        if not model or not isinstance(model, dict):
            # Valid snapshot exists, but has no classes/model -> return empty list
            return []

        classes = model.get("classes", [])
        if not classes:
            return []

        stops = build_codemap_stops(model, graph_store=None, analysis_id=analysis_id, verified_findings=None)
        with _cache_lock:
            _codemap_cache[analysis_id] = stops

        # Persist to disk for this exact snapshot
        try:
            from devlensx.core.persistence import get_storage_manager
            get_storage_manager().save_codemap(snap.repository_id, analysis_id, snap.commit_hash, stops)
        except Exception:
            pass

        return stops
    except Exception:
        return None

def invalidate_codemap(analysis_id: str):
    with _cache_lock:
        _codemap_cache.pop(analysis_id, None)
        _codemap_meta.pop(analysis_id, None)

def invalidate_all():
    """Helper to clear all codemap caches (e.g., on re-analysis or test teardown)."""
    with _cache_lock:
        _codemap_cache.clear()
        _codemap_meta.clear()
