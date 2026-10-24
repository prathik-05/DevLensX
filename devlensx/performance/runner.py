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
        model = intel.model
        rel_count = len(model.get("relationships", [])) or (intel.graph_edge_stats.get("DEPENDS_ON", 0) + intel.graph_edge_stats.get("EXTENDS", 0))
        parse_metrics = t_parse.stop(files_processed=model.get("stats",{}).get("files_parsed",0),
                                     symbols_processed=len(model.get("classes",[])),
                                     relationships_processed=rel_count)

        # Snapshot and Brain registration for consistent benchmark runs
        import subprocess
        from devlensx.evidence.resolver import register_snapshot
        from devlensx.understanding.model.repository_brain import RepositoryBrain
        from devlensx.chat.orchestrator import store_model

        classes = model.get("classes", [])
        brain = RepositoryBrain(str(repo), classes)
        commit = None
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                commit = r.stdout.strip()[:12]
        except Exception:
            pass
        snap = register_snapshot(model.get("repo", repo.name), brain.analysis_run_id, str(repo), commit)
        store_model(brain.analysis_run_id, model)
        run_id = brain.analysis_run_id

        # Wiki
        t_wiki = Timer()
        wiki_pages = []
        try:
            from devlensx.documentation.page_generator import DocumentationPageGenerator
            gen = DocumentationPageGenerator(snap, model, retriever=intel.retriever)
            wiki_pages = gen.generate_all_pages()
        except Exception:
            pass
        wiki_metrics = t_wiki.stop(pages_generated=len(wiki_pages))

        # Diagrams
        t_diag = Timer()
        diagrams_count = 0
        try:
            from devlensx.diagrams.generator import generate_all_diagrams, get_diagram_store
            generate_all_diagrams(snap, model)
            diags = get_diagram_store().list_all(run_id)
            diagrams_count = len(diags)
        except Exception:
            pass
        diag_metrics = t_diag.stop(diagrams_generated=diagrams_count or 1)

        # Chat: FAST / CODEMAP / DEEP_RESEARCH
        t_chat = Timer()
        chat_latencies = {}
        try:
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
                target_sym = classes[0]["name"] if classes else "OwnerController"
                s = time.perf_counter()
                ImpactAnalyzer.analyze(target_sym, run_id)
                ws_lat["impact_ms"] = round((time.perf_counter()-s)*1000,2)
                s = time.perf_counter()
                BuildPlanner.plan("Add pagination", target_sym, run_id)
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
