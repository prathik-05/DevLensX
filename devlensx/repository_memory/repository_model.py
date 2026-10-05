"""Stable data contracts for repository intelligence consumers."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class RetrievalMetrics:
    graph_nodes_requested: int
    vector_chunks_requested: int
    graph_edges_returned: int
    vector_chunks_returned: int
    context_size_chars: int


@dataclass
class RepositoryIntelligence:
    """One analyzed repository and all deterministic intelligence derived from it."""

    repository_path: str
    model: Dict[str, Any]
    graph_store: Any
    retriever: Any
    graph_edge_stats: Dict[str, int] = field(default_factory=dict)
    timings_ms: Dict[str, float] = field(default_factory=dict)

    def retrieve(self, query: str, top_k_graph: int = 10, top_k_vector: int = 5) -> Dict[str, Any]:
        context = self.retriever.retrieve_context(query, top_k_graph, top_k_vector)
        triples = context.get("graph_evidence_triples", [])
        nodes = context.get("relevant_ast_nodes", [])
        context["metrics"] = RetrievalMetrics(
            graph_nodes_requested=top_k_graph,
            vector_chunks_requested=top_k_vector,
            graph_edges_returned=len(triples),
            vector_chunks_returned=len(nodes),
            context_size_chars=len(str(context)),
        ).__dict__
        return context
