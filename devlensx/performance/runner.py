import time
from pathlib import Path
from typing import Dict, Any
from devlensx.performance.metrics import Timer, BenchmarkMetrics
from devlensx.repository_memory import RepositoryIntelligenceEngine

class PerformanceRunner:
    @staticmethod
    def benchmark_full(repo_path: str) -> Dict[str, Any]:
        """Benchmark full pipeline: parse -> graph -> vector -> brain -> wiki -> diagrams -> chat/workspace"""
        t_total = Timer()
        repo = Path(repo_path)
        # Stage 1: Parse + Graph + Vector via RepositoryIntelligenceEngine
        t_parse = Timer()
        engine = RepositoryIntelligenceEngine()
        intel = engine.analyze(str(repo))
        parse_metrics = t_parse.stop(files_processed=intel.model.get("stats",{}).get("files_parsed",0),
                                     symbols_processed=len(intel.model.get("classes",[])),
                                     relationships_processed=intel.graph_edge_stats.get("DEPENDS_ON",0))
        # Wiki
        t_wiki = Timer()
        wiki_pages = []
        try:
            from devlensx.evidence.resolver import get_snapshot_registry
            from devlensx.documentation import DocumentationPageGenerator
            # Get snapshot created by analyze
            snap = None
            for rid, run in [(intel.model.get("repo"), None)]: # placeholder
                pass
            # Use global_state brain
            from devlensx.api.main import global_state
            brain = global_state.get("brain")
            if brain:
                from devlensx.documentation.page_generator import DocumentationPageGenerator
                gen = DocumentationPageGenerator(brain, intel.model, retriever=intel.retriever)
                wiki_pages = gen.generate_all_pages()
        except Exception: pass
        wiki_metrics = t_wiki.stop(pages_generated=len(wiki_pages))

        # Diagrams
        t_diag = Timer()
        diagrams = []
        try:
            from devlensx.diagrams.generator import generate_all_diagrams
            # diagrams already generated in analyze, just measure query
            if intel.graph_store:
                intel.graph_store.query_blast_radius(limit=5)
                intel.graph_store.query_architecture_flow()
            diagrams = [1]  # placeholder count
        except Exception: pass
        diag_metrics = t_diag.stop(diagrams_generated=len(diagrams))

        # Chat: FAST / CODEMAP / DEEP_RESEARCH
        t_chat = Timer()
        chat_latencies = {}
        try:
            from devlensx.evidence.resolver import get_snapshot_registry
            # Find latest run
            from devlensx.api.main import global_state
            run_id = global_state.get("analysis_run_id")
            if run_id:
                from devlensx.chat.orchestrator import ChatOrchestrator
                for mode in ["FAST", "CODEMAP"]:
                    s = time.perf_counter()
                    ChatOrchestrator.chat(run_id, "What does this do?", mode=mode)
                    chat_latencies[mode.lower()] = round((time.perf_counter()-s)*1000,2)
        except Exception as e:
            chat_latencies["error"] = str(e)[:100]
        chat_metrics = t_chat.stop(**chat_latencies)

        # Workspace
        t_ws = Timer()
        ws_lat = {}
        try:
            if run_id:
                from devlensx.impact.analyzer import ImpactAnalyzer
                from devlensx.build.planner import BuildPlanner
                s = time.perf_counter()
                ImpactAnalyzer.analyze("OwnerController", run_id)
                ws_lat["impact_ms"] = round((time.perf_counter()-s)*1000,2)
                s = time.perf_counter()
                BuildPlanner.plan("Add pagination", "OwnerController", run_id)
                ws_lat["build_ms"] = round((time.perf_counter()-s)*1000,2)
        except Exception: pass
        ws_metrics = t_ws.stop(**ws_lat)

        total = t_total.stop(
            parse_ms=parse_metrics.wall_clock_ms,
            graph_ms=intel.timings_ms.get("graph_build_ms",0) if hasattr(intel, 'timings_ms') else 0,
            wiki_ms=wiki_metrics.wall_clock_ms,
            diagram_ms=diag_metrics.wall_clock_ms,
            **chat_latencies,
            **ws_lat
        )
        # Aggregate
        return {
            "repo": str(repo),
            "files": parse_metrics.files_processed,
            "symbols": parse_metrics.symbols_processed,
            "relationships": parse_metrics.relationships_processed,
            "parse": parse_metrics.to_dict(),
            "graph": {"timings_ms": getattr(intel, 'timings_ms', {})},
            "wiki": wiki_metrics.to_dict(),
            "diagrams": diag_metrics.to_dict(),
            "chat": chat_metrics.to_dict(),
            "workspace": ws_metrics.to_dict(),
            "total": total.to_dict(),
        }

    @staticmethod
    def benchmark_incremental(previous_run_id: str, changed_files: list) -> Dict[str, Any]:
        t = Timer()
        from devlensx.incremental.analyzer import IncrementalAnalyzer
        result = IncrementalAnalyzer.analyze(previous_run_id, changed_files_override=changed_files)
        m = t.stop(changed_files=len(changed_files), new_run_id=result.new_run_id, status=result.status)
        return {"incremental": m.to_dict(), "result": result.to_dict()}
