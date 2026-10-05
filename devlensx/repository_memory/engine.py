"""Single orchestration point for parsing, graph construction, and retrieval."""

import logging
from pathlib import Path
from time import perf_counter
from typing import Callable

from devlensx.graph import KuzuGraphStore
from devlensx.parser import parse_repo
from devlensx.retrieval import HybridRetriever

from .repository_model import RepositoryIntelligence

_log = logging.getLogger(__name__)


class RepositoryIntelligenceEngine:
    """Builds deterministic repository intelligence; LLMs consume its output."""

    def __init__(self, parser: Callable = parse_repo, graph_factory=KuzuGraphStore, retriever_factory=HybridRetriever):
        self._parser = parser
        self._graph_factory = graph_factory
        self._retriever_factory = retriever_factory

    def analyze(self, repository_path: str) -> RepositoryIntelligence:
        # Guard: path must exist before any parsing stage
        _p = Path(repository_path)
        if not _p.exists():
            raise FileNotFoundError(
                f"Repository path does not exist: '{repository_path}'. "
                "Provide a valid local path or a GitHub URL for auto-cloning."
            )
        if not any(_p.iterdir()):
            raise ValueError(
                f"Repository directory is empty: '{repository_path}'. Nothing to analyze."
            )

        started = perf_counter()
        _log.info("[Engine] Parsing repository: %s", repository_path)
        model = self._parser(repository_path)
        model["root_path"] = str(Path(repository_path).resolve())
        model["repo_path"] = str(Path(repository_path).resolve())
        parsed_at = perf_counter()
        _log.info("[Engine] Parsed %d symbols in %.2fs",
                  len(model.get("classes", [])), parsed_at - started)

        graph_store = self._graph_factory()
        edge_stats = graph_store.build_from_model(model)
        graph_built_at = perf_counter()
        _log.info("[Engine] Graph built in %.2fs", graph_built_at - parsed_at)

        # Retrieval indexing: non-fatal — analysis proceeds even if vector index fails
        retriever = self._retriever_factory(graph_store)
        try:
            retriever.index_repository_model(model)
        except Exception as _idx_err:
            _log.warning("[Engine] Retrieval indexing failed (non-fatal): %s", _idx_err)
        indexed_at = perf_counter()

        return RepositoryIntelligence(
            repository_path=repository_path,
            model=model,
            graph_store=graph_store,
            retriever=retriever,
            graph_edge_stats=edge_stats,
            timings_ms={
                "parse_ast_ms": round((parsed_at - started) * 1000, 2),
                "graph_build_ms": round((graph_built_at - parsed_at) * 1000, 2),
                "retrieval_index_ms": round((indexed_at - graph_built_at) * 1000, 2),
            },
        )
