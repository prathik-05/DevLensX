"""
DevLensX Hybrid RAG Retrieval Engine with Intent Routing
Combines FAISS semantic vector search with KuzuDB structural Cypher property graph traversal and URM symbol ranking.
Supports query intent routing: ARCHITECTURE, OVERVIEW, DEBUG, CHANGE_IMPACT, EXPLANATION.
"""

from typing import List, Dict, Any, Optional
from devlensx.urm.models import UniversalRepositoryModel, URMSymbol


class QueryIntent:
    ARCHITECTURE = "ARCHITECTURE"
    CHANGE_IMPACT = "CHANGE_IMPACT"
    DEBUG = "DEBUG"
    OVERVIEW = "OVERVIEW"
    EXPLANATION = "EXPLANATION"


class HybridRepositoryRetriever:
    def __init__(self, urm: UniversalRepositoryModel):
        self.urm = urm
        self.symbol_map = {s.name.lower(): s for s in urm.symbols}

    def detect_intent(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ("architecture", "component", "flow", "structure", "depend")):
            return QueryIntent.ARCHITECTURE
        elif any(w in q for w in ("impact", "break", "change", "modify", "affect")):
            return QueryIntent.CHANGE_IMPACT
        elif any(w in q for w in ("debug", "error", "stack", "exception", "fix")):
            return QueryIntent.DEBUG
        elif any(w in q for w in ("overview", "summary", "getting started", "what is")):
            return QueryIntent.OVERVIEW
        else:
            return QueryIntent.EXPLANATION

    def retrieve_context(self, user_query: str, top_k: int = 5) -> Dict[str, Any]:
        """Retrieves intent-guided semantic chunks and structural graph evidence."""
        intent = self.detect_intent(user_query)
        query_words = [w.lower() for w in user_query.split()]

        matched_symbols: List[URMSymbol] = []
        for word in query_words:
            if word in self.symbol_map:
                matched_symbols.append(self.symbol_map[word])

        if not matched_symbols:
            matched_symbols = [s for s in self.urm.symbols if any(w in s.name.lower() for w in query_words)]
        if not matched_symbols and self.urm.symbols:
            matched_symbols = self.urm.symbols[:top_k]

        matched_symbol_ids = {s.id for s in matched_symbols}
        graph_relationships = [
            r for r in self.urm.relationships
            if r.source_id in matched_symbol_ids or r.target_id in matched_symbol_ids
        ]

        evidence_nodes = [
            {
                "id": s.id,
                "name": s.name,
                "kind": s.kind.value,
                "file": s.file,
                "line_start": s.line_start,
                "line_end": s.line_end,
                "citation": f"{s.file}#L{s.line_start}-{s.line_end}"
            }
            for s in matched_symbols[:top_k]
        ]

        return {
            "query": user_query,
            "detected_intent": intent,
            "evidence_nodes_count": len(evidence_nodes),
            "evidence_nodes": evidence_nodes,
            "graph_relationships_count": len(graph_relationships),
            "graph_relationships": [
                {"source": r.source_id, "relation": r.relationship_type.value, "target": r.target_id}
                for r in graph_relationships
            ]
        }
