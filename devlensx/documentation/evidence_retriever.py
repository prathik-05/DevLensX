"""
DevLensX Documentation Evidence Context Partitioner (D7.2)

Formats bounded EvidenceScope into explicit, partitioned context channels
with clear trust levels:
1. DETERMINISTIC STRUCTURAL EVIDENCE (URM / AST) — Can directly prove claims ✅
2. DETERMINISTIC GRAPH RELATIONSHIPS (Kuzu) — Can directly prove relationships ✅
3. DETERMINISTIC SOURCE & CONFIG EXCERPTS (D5) — Can directly prove lines ✅
4. DETERMINISTIC VISUAL EVIDENCE (D6) — Can directly prove topology ✅
5. DERIVED SEMANTIC CONTEXT (FAISS) — Background context only (Cannot prove truth) ❌
"""

from typing import Dict, Any, List
from devlensx.documentation.models import EvidenceScope


class EvidenceRetriever:
    """Partitions and formats an EvidenceScope into prompt-ready context blocks with explicit trust levels."""

    @staticmethod
    def partition_context(scope: EvidenceScope) -> Dict[str, str]:
        # 1. Deterministic Structural Facts (URM)
        struct_lines = []
        for s in scope.symbols[:15]:
            st = s.get("stereotype") or s.get("kind") or "symbol"
            struct_lines.append(f"- Symbol: `{s.get('name')}` | Stereotype: `{st}` | File: `{s.get('file')}` (Lines {s.get('line_start')}-{s.get('line_end')})")
        structural_block = "\n".join(struct_lines) if struct_lines else "No direct structural symbols bound."

        # 2. Deterministic Graph Relationships (Kuzu)
        rel_lines = []
        for r in scope.relationships[:20]:
            rel_lines.append(f"- Relationship: `{r.get('source')}` --[{r.get('type', 'DEPENDS_ON')}]--> `{r.get('target')}`")
        relationship_block = "\n".join(rel_lines) if rel_lines else "No explicit inter-component relationships bound."

        # 3. Deterministic Source & Config Evidence (D5)
        d5_lines = []
        for ref in scope.evidence_refs[:10]:
            d5_lines.append(f"- Provenance Citation: `{ref.to_citation()}` for `{ref.symbol_name or 'symbol'}`")
        d5_block = "\n".join(d5_lines) if d5_lines else "No source citations available."

        # 4. Deterministic Visual Diagrams (D6)
        diagram_block = f"Associated Verified Diagrams: {', '.join(scope.diagram_ids)}" if scope.diagram_ids else "No diagrams bound."

        # 5. Derived Semantic Context (FAISS - Explicitly NOT deterministic truth)
        semantic_lines = []
        for c in scope.semantic_chunks[:3]:
            snippet = c.get("snippet", "").strip().replace("\n", " ")[:160]
            semantic_lines.append(f"- Excerpt ({c.get('file')}): \"{snippet}...\"")
        semantic_block = "\n".join(semantic_lines) if semantic_lines else "No semantic retrieval context available."

        return {
            "structural_evidence": structural_block,
            "relationship_evidence": relationship_block,
            "source_citations": d5_block,
            "diagram_evidence": diagram_block,
            "semantic_context": semantic_block,
        }

    @classmethod
    def build_prompt_context(cls, scope: EvidenceScope) -> str:
        """Assembles the complete partitioned prompt string with trust annotations."""
        p = cls.partition_context(scope)
        return (
            f"=== 1. DETERMINISTIC STRUCTURAL EVIDENCE (Verified Truth) ===\n{p['structural_evidence']}\n\n"
            f"=== 2. DETERMINISTIC GRAPH RELATIONSHIPS (Verified Truth) ===\n{p['relationship_evidence']}\n\n"
            f"=== 3. DETERMINISTIC SOURCE CITATIONS (Verified Truth) ===\n{p['source_citations']}\n\n"
            f"=== 4. DETERMINISTIC VISUAL EVIDENCE (D6 Diagrams) ===\n{p['diagram_evidence']}\n\n"
            f"=== 5. DERIVED SEMANTIC CONTEXT (Background Reference Only - Cannot directly prove claims) ===\n{p['semantic_context']}\n"
        )
