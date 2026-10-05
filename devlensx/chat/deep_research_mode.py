"""Deep Research mode — multi-stage research."""

from typing import Dict, Any, Optional, List
from devlensx.evidence.models import SnapshotRecord
from devlensx.chat.models import ChatMode, ChatContext, VerifiedAnswer
from devlensx.chat.research_planner import plan_research
from devlensx.chat.evidence_context import collect_evidence
from devlensx.chat.synthesis import synthesize_answer


def run_deep_research(
    snapshot: SnapshotRecord,
    model: Dict[str, Any],
    user_query: str,
    context: Optional[ChatContext],
    on_progress=None,
) -> VerifiedAnswer:
    # Evidence budget — prevents uncontrolled scan
    MAX_SUBQUESTIONS = 6
    MAX_FILES = 20
    MAX_SOURCE_EXCERPTS = 12
    MAX_GRAPH_HOPS = 3

    subquestions = plan_research(user_query, max_subquestions=MAX_SUBQUESTIONS)[:MAX_SUBQUESTIONS]
    if on_progress:
        on_progress("research_planned", {"subquestions": subquestions})

    # Parallel retrieval per subquestion (sequential here, but distinct evidence sets)
    all_symbols: Dict[str, Dict] = {}
    all_rels: Dict[str, Dict] = {}
    all_refs: List[Dict] = []

    for idx, sq in enumerate(subquestions):
        if on_progress:
            on_progress("retrieval_started", {"channel": "subquestion", "subquestion": sq, "index": idx})
        ev = collect_evidence(snapshot, model, sq, context, top_k=6)
        for s in ev.deterministic_symbols:
            all_symbols[s["name"]] = s
        for r in ev.deterministic_relationships:
            key = f"{r.get('source')}->{r.get('target')}"
            all_rels[key] = r
        all_refs.extend(ev.deterministic_source_refs)
        if on_progress:
            on_progress("evidence_found", {"subquestion": sq, "symbols": len(ev.deterministic_symbols)})

    from devlensx.chat.models import ChatEvidence
    consolidated = ChatEvidence(
        deterministic_symbols=list(all_symbols.values())[:18],
        deterministic_relationships=list(all_rels.values())[:18],
        deterministic_source_refs=all_refs[:MAX_SOURCE_EXCERPTS],
        total_symbols=len(all_symbols),
        total_relationships=len(all_rels),
    )

    if on_progress:
        on_progress("synthesis_started", {})

    answer, claims, refs = synthesize_answer(
        user_query, consolidated, mode=ChatMode.DEEP_RESEARCH.value,
        snapshot=snapshot,
        classes=model.get("classes", []),
        relationships=model.get("relationships", []),
    )

    # Structured research report
    structured = (
        f"# Research Report\n\n"
        f"## Executive Summary\n{answer[:600]}\n\n"
        f"## Evidence\n"
        f"- {len(consolidated.deterministic_symbols)} symbols, "
        f"{len(consolidated.deterministic_relationships)} relationships, "
        f"{len(consolidated.deterministic_source_refs)} source ranges\n\n"
        f"## Detailed Answer\n{answer}\n"
    )

    research = {
        "subquestions": subquestions,
        "completed": True,
        "evidence": {
            "symbols": len(consolidated.deterministic_symbols),
            "relationships": len(consolidated.deterministic_relationships),
            "source_ranges": len(consolidated.deterministic_source_refs),
        },
        "budget": {
            "max_subquestions": MAX_SUBQUESTIONS,
            "max_files": MAX_FILES,
            "max_source_excerpts": MAX_SOURCE_EXCERPTS,
            "max_graph_hops": MAX_GRAPH_HOPS,
        },
    }

    return VerifiedAnswer(
        answer=structured,
        mode=ChatMode.DEEP_RESEARCH,
        repository_id=snapshot.repository_id,
        analysis_run_id=snapshot.analysis_run_id,
        commit_hash=snapshot.commit_hash,
        context=context.to_dict() if context and hasattr(context, "to_dict") else (context.__dict__ if context else None),
        claims=claims,
        evidence_refs=refs,
        diagrams=[{"type": "RESEARCH_GRAPH", "subquestions": subquestions}],
        research=research,
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