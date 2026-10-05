"""Fast mode — intent -> targeted retrieval -> synthesis -> verification."""

from typing import Dict, Any, Optional
from devlensx.evidence.models import SnapshotRecord
from devlensx.chat.models import ChatMode, ChatContext, VerifiedAnswer
from devlensx.chat.evidence_context import collect_evidence
from devlensx.chat.synthesis import synthesize_answer


def run_fast(
    snapshot: SnapshotRecord,
    model: Dict[str, Any],
    user_query: str,
    context: Optional[ChatContext],
) -> VerifiedAnswer:
    evidence = collect_evidence(snapshot, model, user_query, context, top_k=8)

    answer, claims, refs = synthesize_answer(
        user_query, evidence, mode=ChatMode.FAST.value,
        snapshot=snapshot,
        classes=model.get("classes", []),
        relationships=model.get("relationships", []),
    )

    # Small evidence set, low latency
    return VerifiedAnswer(
        answer=answer,
        mode=ChatMode.FAST,
        repository_id=snapshot.repository_id,
        analysis_run_id=snapshot.analysis_run_id,
        commit_hash=snapshot.commit_hash,
        context=context.to_dict() if hasattr(context, "to_dict") else (context.__dict__ if context else None),
        claims=claims,
        evidence_refs=refs or evidence.deterministic_source_refs,
        diagrams=evidence.diagrams[:1],
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