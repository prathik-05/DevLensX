"""Evidence consolidation with explicit trust levels.
Deterministic evidence (URM/Kuzu/D5/D6) can prove claims; FAISS cannot.
"""

from typing import Dict, Any, List, Optional
from devlensx.evidence.models import SnapshotRecord
from devlensx.documentation.evidence_scope import EvidenceScopeBuilder
from devlensx.documentation.evidence_retriever import EvidenceRetriever
from devlensx.chat.models import ChatEvidence, ChatContext
from devlensx.chat.context import build_context_query


def collect_evidence(
    snapshot: SnapshotRecord,
    model: Dict[str, Any],
    user_query: str,
    context: Optional[ChatContext] = None,
    top_k: int = 12,
) -> ChatEvidence:
    context_query = build_context_query(context, user_query)

    # Determine page blueprint for scope: use context page if present else overview-like
    page_id = context.page_id if context and context.page_id else "chat-global"
    blueprint = {"id": page_id, "title": page_id, "type": page_id}

    # Bounded scope via D7 builder (adds deterministic symbols/relationships/refs)
    scope = EvidenceScopeBuilder.build_scope(
        page_id=page_id,
        page_blueprint=blueprint,
        snapshot=snapshot,
        model=model,
        retriever=None,
    )

    # Contextual boost: if a symbol is selected, ensure it is in the scope
    if context and context.selected_symbol:
        sel = context.selected_symbol
        if not any(s.get("name") == sel for s in scope.symbols):
            for c in model.get("classes", []):
                if c.get("name") == sel:
                    scope.symbols.insert(0, c)
                    # also add its relationships
                    for r in model.get("relationships", []):
                        if sel in (str(r.get("source")), str(r.get("target"))):
                            if r not in scope.relationships:
                                scope.relationships.append(r)
                    break

    # Deterministic source refs are already in scope.evidence_refs (D5 bound)
    evidence = ChatEvidence(
        deterministic_symbols=scope.symbols[:top_k],
        deterministic_relationships=scope.relationships[:20],
        deterministic_source_refs=[r.to_dict() for r in scope.evidence_refs[:8]],
        semantic_chunks=scope.semantic_chunks[:3],
        diagrams=[{"id": d} for d in scope.diagram_ids],
        total_symbols=len(scope.symbols),
        total_relationships=len(scope.relationships),
    )

    # If still empty (tiny repo), fall back to raw model samples so answer is not hallucinated
    if evidence.is_empty() and model.get("classes"):
        evidence.deterministic_symbols = model["classes"][: top_k // 2]
        evidence.total_symbols = len(model["classes"])

    return evidence