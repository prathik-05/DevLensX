"""Codemap mode — graph-first traversal."""

from typing import Dict, Any, Optional, List
from devlensx.evidence.models import SnapshotRecord
from devlensx.chat.models import ChatMode, ChatContext, VerifiedAnswer
from devlensx.chat.evidence_context import collect_evidence
from devlensx.chat.synthesis import synthesize_answer


def _find_start_symbols(model: Dict[str, Any], query: str) -> List[str]:
    q = query.lower()
    q_words = {w.strip(".,!?;:\"'()[]") for w in q.split() if len(w) > 2}
    scored = []
    for c in model.get("classes", []):
        # Only consider class-level symbols for codemap entry points
        if c.get("kind") not in ("class", "struct", "interface", "enum") and c.get("stereotype") not in ("Controller", "Service", "Repository", "Component", "Endpoint"):
            continue
        if c.get("is_test") or "Test" in c.get("name",""):
            continue
        name = c.get("name","")
        n_low = name.lower()
        best = 0
        for w in q_words:
            if w in n_low or n_low in w:
                best = max(best, len(w))
        if best == 0:
            continue
        bonus = 0
        if c.get("stereotype") in ("Controller", "Endpoint", "Service", "Repository"):
            bonus = 10
        scored.append((best + bonus, len(name), name))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    candidates = [name for _, _, name in scored[:3]]
    if not candidates:
        # Fallback: endpoints/controllers are natural entry points
        for c in model.get("classes", []):
            if c.get("stereotype") in ("Controller", "Endpoint") and not c.get("is_test"):
                candidates.append(c["name"])
                if len(candidates) >= 2:
                    break
    # Deduplicate preserving order
    seen = set()
    uniq = []
    for n in candidates:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq[:3]


def _traverse(model: Dict[str, Any], starts: List[str], max_depth: int = 6) -> List[Dict[str, Any]]:
    # BFS over relationships (source/target are names)
    rels = model.get("relationships", [])
    adj: Dict[str, List[str]] = {}
    for r in rels:
        s, t = str(r.get("source")), str(r.get("target"))
        adj.setdefault(s, []).append(t)
    visited = set()
    order: List[str] = []
    queue = [(s, 0) for s in starts]
    for s, _ in queue:
        visited.add(s)
        order.append(s)
    idx = 0
    while idx < len(queue):
        cur, d = queue[idx]; idx += 1
        if d >= max_depth:
            continue
        for nxt in adj.get(cur, []):
            if nxt not in visited:
                visited.add(nxt)
                order.append(nxt)
                queue.append((nxt, d+1))
    # Return relationship path that connects the traversal order
    path_rels = []
    for r in rels:
        if str(r.get("source")) in visited and str(r.get("target")) in visited:
            path_rels.append(r)
    return order, path_rels[:12]


def run_codemap(
    snapshot: SnapshotRecord,
    model: Dict[str, Any],
    user_query: str,
    context: Optional[ChatContext],
) -> VerifiedAnswer:
    starts = _find_start_symbols(model, user_query)
    order, path_rels = _traverse(model, starts)

    # Build a small diagram descriptor that reuses D6 store shape
    diagram = {
        "type": "CALL_GRAPH",
        "nodes": [{"id": n, "label": n} for n in order[:12]],
        "edges": [{"source": r.get("source"), "target": r.get("target"), "type": r.get("type")} for r in path_rels],
    }

    # Evidence is the traversed subgraph
    from devlensx.chat.models import ChatEvidence
    evidence = collect_evidence(snapshot, model, user_query, context, top_k=6)
    # Override with graph-traversal evidence
    evidence.deterministic_symbols = [c for c in model.get("classes", []) if c.get("name") in order][:8]
    evidence.deterministic_relationships = path_rels

    answer, claims, refs = synthesize_answer(
        user_query, evidence, mode=ChatMode.CODEMAP.value,
        snapshot=snapshot,
        classes=model.get("classes", []),
        relationships=model.get("relationships", []),
    )

    # Prepend the path for immediate visual grounding
    if order:
        path_str = " -> ".join(order[:8])
        answer = f"Codemap path: {path_str}\n\n{answer}"

    return VerifiedAnswer(
        answer=answer,
        mode=ChatMode.CODEMAP,
        repository_id=snapshot.repository_id,
        analysis_run_id=snapshot.analysis_run_id,
        commit_hash=snapshot.commit_hash,
        context=context.to_dict() if context and hasattr(context, "to_dict") else (context.__dict__ if context else None),
        claims=claims,
        evidence_refs=refs if refs else [
            r if isinstance(r, dict) else r.to_dict()
            for r in evidence.deterministic_source_refs[:4]
        ],
        diagrams=[diagram],
        verification_summary=_summarize(claims),
    )


def _summarize(claims):
    s = {"verified": 0, "suggestions": 0, "insufficient_evidence": 0}
    for c in claims:
        v = c.get("verdict","") if isinstance(c, dict) else getattr(c.verdict, "value", str(c.verdict))
        if "VERIFIED" in v:
            s["verified"] += 1
        elif "SUGGESTION" in v or "PARTIAL" in v:
            s["suggestions"] += 1
        else:
            s["insufficient_evidence"] += 1
    return s