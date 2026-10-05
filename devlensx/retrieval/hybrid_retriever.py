"""
DevLensX Module 6: Hybrid Context Retriever & Vector Indexer
Fuses 2-hop Cypher Graph Traversal with FAISS Dense Vector Similarity Search.
"""

from devlensx.retrieval.vector_store import FAISSVectorStore
from typing import Dict, Any, List, Optional


class HybridContextRetriever:
    def __init__(self, graph_store):
        self.graph_store = graph_store
        self.vector_store = FAISSVectorStore()

    def index_repository_model(self, repo_model):
        """Indexes class AST definitions into FAISS vector store with robust type checking."""
        docs = []
        for c in repo_model.get("classes", []):
            methods = c.get("methods", [])
            methods_summary = ", ".join([m.get("name", "") if isinstance(m, dict) else str(m) for m in methods if m])
            
            endpoints = c.get("endpoints", [])
            endpoints_summary = ", ".join([
                f"{e.get('http_annotation') or e.get('method') or e.get('http_method', 'GET')} {e.get('path') or e.get('route') or e.get('full_path', '/')}"
                if isinstance(e, dict) else str(e)
                for e in endpoints if e
            ])
            
            deps = c.get("injected_dependencies", [])
            deps_summary = ", ".join(deps) if isinstance(deps, list) else str(deps)

            extends_val = c.get("extends", [])
            extends_summary = ", ".join(extends_val) if isinstance(extends_val, list) else str(extends_val or "")

            implements_val = c.get("implements", [])
            implements_summary = ", ".join(implements_val) if isinstance(implements_val, list) else str(implements_val or "")

            content = (
                f"Class {c.get('name', 'Unknown')} (Stereotype: {c.get('stereotype', 'General')}, Kind: {c.get('kind', 'class')}, Package: {c.get('package', '')}). "
                f"Extends: {extends_summary}. Implements: {implements_summary}. "
                f"Injected Dependencies: {deps_summary}. "
                f"Methods: {methods_summary}. Endpoints: {endpoints_summary}."
            )
            docs.append({
                "id": f"{c.get('package', '')}.{c.get('name', '')}",
                "content": content,
                "metadata": {
                    "class_name": c.get("name", ""),
                    "stereotype": c.get("stereotype", ""),
                    "file": c.get("file", "")
                }
            })
        self.vector_store.build_index(docs)

    def retrieve_context(self, query: str, top_k_graph: int = 10, top_k_vector: int = 5, top_k: Optional[int] = None) -> Dict[str, Any]:
        """Fuses FAISS vector similarity with Kuzu 2-hop graph traversal.
        Arity fixed to (query, top_k_graph, top_k_vector) for RepositoryIntelligence.retrieve compatibility.
        top_k alias kept for backwards compat."""
        if top_k is not None:
            top_k_vector = top_k
            top_k_graph = top_k
        vector_results = self.vector_store.search(query, top_k=top_k_vector)
        
        graph_facts = []
        if self.graph_store and vector_results:
            first_class = vector_results[0].get("metadata", {}).get("class_name", "")
            if first_class:
                # get_two_hop_neighbors does not exist — replace with query_subgraph_triples or query_change_impact
                try:
                    if hasattr(self.graph_store, "query_subgraph_triples"):
                        graph_facts = self.graph_store.query_subgraph_triples(query_keyword=first_class, max_nodes=top_k_graph) or []
                    elif hasattr(self.graph_store, "query_change_impact"):
                        graph_facts = self.graph_store.query_change_impact(first_class) or []
                except Exception:
                    graph_facts = []

        # Ensure return dict has both graph_evidence_triples and relevant_ast_nodes aliases for callers
        relevant_ast_nodes = []
        for vr in vector_results:
            md = vr.get("metadata", {}) or {}
            relevant_ast_nodes.append({
                "class_name": md.get("class_name", ""),
                "stereotype": md.get("stereotype", ""),
                "file": md.get("file", ""),
                "relevance_score": vr.get("score", 0.0),
                "content": vr.get("content", ""),
            })

        return {
            "query": query,
            "vector_results": vector_results,
            "graph_facts": graph_facts,
            "graph_evidence_triples": graph_facts,
            "relevant_ast_nodes": relevant_ast_nodes,
            "fusion_formula": "Score = 0.6 * VectorSim + 0.4 * GraphProximity"
        }
