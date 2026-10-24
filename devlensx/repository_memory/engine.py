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
        model = None
        fallback_used = False
        try:
            model = self._parser(repository_path)
        except Exception as _parse_err:
            _log.warning("[Engine] Native parse encountered error: %s. Attempting controlled Gitingest fallback.", _parse_err)

        # Controlled Gitingest fallback when native parser extracts 0 classes/files
        if not model or not model.get("classes"):
            try:
                from gitingest import ingest
                _summary, _tree, _content = ingest(repository_path)
                fallback_used = True
                _log.info("[Engine] Gitingest fallback recovered context for %s (%d chars).", repository_path, len(_content or ""))
                if not model:
                    model = {
                        "repo": Path(repository_path).name,
                        "stats": {"files_parsed": 0, "files_failed": 0, "symbols_extracted": 0},
                        "classes": [],
                        "relationships": [],
                        "repo_summary": {"language": "Unknown", "total_classes": 0, "total_relationships": 0, "total_endpoints": 0},
                    }
                # Extract structural declarations from Gitingest text without fabricating verified AST line ranges
                if not model.get("classes") and _content:
                    import re
                    synth = []
                    curr_file = ""
                    file_line = 0
                    for l in _content.splitlines():
                        fm = re.search(r"^={3,}\s*File:\s*(.*?)\s*={3,}$", l)
                        if fm:
                            curr_file = fm.group(1).strip()
                            file_line = 0
                            continue
                        file_line += 1
                        dm = re.search(r"^\s*(?:public\s+|export\s+|async\s+)*(?:class|interface|def|function)\s+([A-Za-z0-9_]{2,})", l)
                        if dm and curr_file:
                            sym_name = dm.group(1)
                            # Key on (file, name) to preserve distinct symbols across different files
                            if not any(x["file"] == curr_file and x["name"] == sym_name for x in synth):
                                synth.append({
                                    "name": sym_name,
                                    "file": curr_file,
                                    "stereotype": "InferredDeclaration",
                                    "line_start": file_line if file_line > 0 else None,
                                    "line_end": file_line if file_line > 0 else None,
                                    "provenance": "GITINGEST_TEXT_FALLBACK",
                                    "confidence": "INFERRED",
                                    "is_ast_verified": False,
                                    "methods": []
                                })
                    if synth:
                        model["inferred_declarations"] = synth[:100]
                        model["classes"] = synth[:100]
                        model["stats"]["symbols_extracted"] = len(synth)
                        _log.info("[Engine] Extracted %d inferred declarations (provenance: GITINGEST_TEXT_FALLBACK).", len(synth))

                model["gitingest_fallback"] = {
                    "used": True,
                    "summary": _summary,
                    "tree": _tree,
                    "content_length": len(_content or ""),
                    "inferred_symbol_count": len(model.get("inferred_declarations", [])),
                    "provenance": "GITINGEST_TEXT_FALLBACK",
                    "confidence": "INFERRED"
                }
            except Exception as _git_err:
                _log.warning("[Engine] Gitingest fallback not available: %s", _git_err)
                if not model:
                    raise

        model["root_path"] = str(Path(repository_path).resolve())
        model["repo_path"] = str(Path(repository_path).resolve())
        parsed_at = perf_counter()
        _log.info("[Engine] Parsed %d symbols in %.2fs (fallback: %s)",
                  len(model.get("classes", [])), parsed_at - started, fallback_used)

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
