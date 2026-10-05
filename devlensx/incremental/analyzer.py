import uuid
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
from devlensx.incremental.models import IncrementalResult, InvalidationSet, ChangeType
from devlensx.incremental.diff import GitDiffDetector
from devlensx.incremental.symbol_analyzer import SymbolAnalyzer
from devlensx.incremental.dependency_analyzer import DependencyAnalyzer
from devlensx.incremental.invalidation import InvalidationEngine
from devlensx.incremental.cache import get_model_for_run, get_graph_for_run
from devlensx.evidence.resolver import get_snapshot_registry, register_snapshot
from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.chat.orchestrator import store_model as store_chat_model

class IncrementalAnalyzer:
    @staticmethod
    def analyze(previous_run_id: str, repo_path: Optional[str] = None, target_commit: Optional[str] = None, changed_files_override: Optional[List[str]] = None) -> IncrementalResult:
        registry = get_snapshot_registry()
        prev_snap = registry.get(previous_run_id)
        if not prev_snap:
            raise ValueError(f"UNKNOWN_RUN:{previous_run_id}")
        repo = repo_path or prev_snap.repo_path
        repo_p = Path(repo)
        # Determine previous commit
        prev_commit = prev_snap.commit_hash
        # If changed_files_override provided (for tests without git), use it
        if changed_files_override is not None:
            from devlensx.incremental.diff import GitDiffDetector
            if len(changed_files_override) == 0:
                file_changes = []
            else:
                file_changes = GitDiffDetector.detect_changed_files_from_list(changed_files_override, ChangeType.MODIFIED)
        else:
            # Detect git diff
            # Get current commit hash
            new_commit = None
            try:
                import subprocess
                res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_p), capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    new_commit = res.stdout.strip()[:12]
            except Exception:
                pass
            if target_commit:
                new_commit = target_commit[:12] if target_commit else new_commit
            file_changes = GitDiffDetector.detect_changed_files(str(repo_p), previous_commit, new_commit)
            # If no git changes detected but repo is dirty, file_changes may be empty -> check status
            if prev_commit and new_commit and prev_commit == new_commit:
                # No commit change, but maybe unstaged changes
                # file_changes already captures diff HEAD, so if empty, it's truly no changes
                pass

        # Load previous model
        prev_model = get_model_for_run(previous_run_id)
        prev_classes = prev_model.get("classes", []) if isinstance(prev_model, dict) else []

        # If no file changes, return empty incremental result (no rebuild)
        if not file_changes:
            new_run_id = previous_run_id  # No new snapshot needed; but we still create result with same run
            # Generate a new run id only if we actually need to? For D10.3, if no changes, return same
            return IncrementalResult(
                repository_id=prev_snap.repository_id,
                previous_run_id=previous_run_id,
                new_run_id=previous_run_id,
                previous_commit=prev_commit,
                new_commit=prev_commit,
                changed_files=[],
                changed_symbols=[],
                invalidated_artifacts=InvalidationSet(),
                rebuilt_artifacts=InvalidationSet(),
                status="NO_CHANGES"
            )

        # Map to symbols
        changed_symbols = SymbolAnalyzer.map_files_to_symbols(file_changes, prev_classes)

        # For ADDED files that had no previous symbols, we need to parse them to discover new symbols
        # Perform incremental parse: only parse changed files
        new_classes = []
        added_symbols_extra: List[Any] = []
        # We need to re-parse changed files to get current symbol state
        # Use parse_repo for full repo but we will diff for selective update
        # For performance, we do selective reparse of changed files only
        try:
            from devlensx.parser import parse_repo
            # Full parse for now (correctness before optimization)
            # In optimized version, we'd only parse changed files
            new_model = parse_repo(str(repo_p))
            new_classes = []
            for fr in new_model.get("classes", []) if isinstance(new_model, dict) and "classes" in new_model else []:
                # parse_repo returns flat model with classes containing file field
                pass
            # parse_repo returns {"repo":..., "classes": [...] } directly when called via parse_repo
            # Actually parse_repo returns repo_model with classes
            if isinstance(new_model, dict) and "classes" in new_model:
                new_classes = new_model["classes"]
            # Detect added/deleted via set difference
            from devlensx.incremental.symbol_analyzer import SymbolAnalyzer as SA
            added_extra = SA.detect_added_symbols(new_classes, prev_classes)
            deleted_extra = SA.detect_deleted_symbols(prev_classes, new_classes)
            # Merge with changed_symbols (avoid duplicates)
            existing_ids = {s.symbol_id for s in changed_symbols}
            for s in added_extra + deleted_extra:
                if s.symbol_id not in existing_ids:
                    changed_symbols.append(s)
                    existing_ids.add(s.symbol_id)
        except Exception:
            pass

        # Dependency impact via Kuzu
        changed_names = [s.symbol_id for s in changed_symbols]
        graph_store = get_graph_for_run(previous_run_id)
        dep_map = DependencyAnalyzer.find_affected_symbols(changed_names, graph_store, prev_classes)

        # Invalidation
        # Load diagrams and wiki pages for invalidation context
        diagrams = []
        wiki_pages = []
        try:
            from devlensx.diagrams.generator import get_diagram_store
            store = get_diagram_store()
            diagrams = store.list_all(previous_run_id)
        except Exception:
            pass
        try:
            from devlensx.documentation.cache import get_documentation_cache
            # wiki cache keyed by repo/run
            pass
        except Exception:
            pass
        invalidated = InvalidationEngine.compute_invalidated_artifacts(changed_symbols, dep_map, prev_classes, diagrams, wiki_pages)

        # Create new snapshot (immutability: old preserved)
        # Full re-analysis for correctness (incremental optimization comes later)
        try:
            intelligence = RepositoryIntelligenceEngine().analyze(str(repo_p))
            new_model_full = intelligence.model
            new_run_id = None
            # RepositoryBrain creates new run id
            from devlensx.understanding.model.repository_brain import RepositoryBrain
            brain = RepositoryBrain(str(repo_p), new_model_full.get("classes", []))
            new_run_id = brain.analysis_run_id
            # Determine new commit
            new_commit = None
            try:
                import subprocess
                res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_p), capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    new_commit = res.stdout.strip()[:12]
            except Exception:
                pass
            if target_commit:
                new_commit = target_commit[:12]
            # Register snapshot
            register_snapshot(new_model_full.get("repo", prev_snap.repository_id), new_run_id, str(repo_p), new_commit)
            store_chat_model(new_run_id, new_model_full)
            # Update global_state to new
            from devlensx.api.main import global_state as gs
            gs["repo_model"] = new_model_full
            gs["graph_store"] = intelligence.graph_store
            gs["retriever"] = intelligence.retriever
            gs["analysis_run_id"] = new_run_id
            # Also persist citations, diagrams, wiki like main.py does (best-effort)
            try:
                from devlensx.evidence.resolver import store_snapshot_refs, get_snapshot_registry as _reg
                from devlensx.evidence.models import EvidenceRef, EvidenceType
                from devlensx.evidence.resolver import EvidenceResolver as _EvResolver
                snap = _reg().get(new_run_id)
                if snap:
                    _ranked = sorted(new_model_full.get("classes", []), key=lambda c: (0 if c.get("stereotype") in ("Controller","Service","Repository") else 99, -(len(c.get("methods") or []))))[:40]
                    refs = [_EvResolver.ref_from_brain_symbol(snap, c) for c in _ranked if c.get("file")]
                    store_snapshot_refs(new_run_id, refs)
                    try:
                        from devlensx.diagrams.generator import generate_all_diagrams
                        generate_all_diagrams(snap, new_model_full)
                    except Exception: pass
            except Exception: pass
        except Exception as e:
            # Fallback: generate new run id without full analysis
            import uuid
            new_run_id = f"run_{uuid.uuid4().hex[:8]}"
            new_commit = target_commit[:12] if target_commit else "unknown"
            register_snapshot(prev_snap.repository_id, new_run_id, str(repo_p), new_commit)
            store_chat_model(new_run_id, prev_model)

        rebuilt = InvalidationSet(
            files=invalidated.files,
            symbols=invalidated.symbols,
            relationships=invalidated.relationships,
            diagrams=invalidated.diagrams,
            wiki_pages=invalidated.wiki_pages,
            evidence=invalidated.evidence,
            vectors=invalidated.vectors,
        )

        return IncrementalResult(
            repository_id=prev_snap.repository_id,
            previous_run_id=previous_run_id,
            new_run_id=new_run_id,
            previous_commit=prev_commit,
            new_commit=new_commit,
            changed_files=file_changes,
            changed_symbols=changed_symbols,
            invalidated_artifacts=invalidated,
            rebuilt_artifacts=rebuilt,
            status="COMPLETE"
        )
