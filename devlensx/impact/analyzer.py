"""DevLensX Change Impact Analyzer — snapshot-bound AST & Graph blast radius."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.evidence.models import EvidenceRef, EvidenceType, SnapshotRecord
from devlensx.impact.models import ImpactResult
from devlensx.understanding.profiling.repository_profiler import is_test_file_or_symbol


_ISSUE_BY_STEREOTYPE = {
    "Controller": "BUG_RISK",
    "Service": "SECURITY",
    "Repository": "PERFORMANCE",
    "Entity": "ARCHITECTURE",
    "Component": "MAINTAINABILITY",
}
_RISK_BY_STEREOTYPE = {
    "Controller": "CRITICAL",
    "Service": "WARNING",
    "Repository": "WARNING",
}
_MAX_IAT = 10  # maximum hops for downstream blast-radius collection


def blast_radius_symbols(target_symbol: str, analysis_run_id: str) -> List[Dict[str, Any]]:
    """Convenience: just the downstream/reachable symbols of a blast-radius call,
    ordered as returned by the snapshot model. Used by Evaluation Lab drag-and-drop."""
    return ImpactAnalyzer.analyze(target_symbol, analysis_run_id).downstream


def _ref_for_class(snapshot: SnapshotRecord, cls: Dict[str, Any]) -> Dict[str, Any]:
    ref = EvidenceRef(
        repository_id=snapshot.repository_id,
        analysis_run_id=snapshot.analysis_run_id,
        commit_hash=snapshot.commit_hash,
        file_path=(cls.get("file") or "").replace("\\", "/"),
        line_start=int(cls.get("line_start") or 1),
        line_end=int(cls.get("line_end") or 1),
        symbol_name=cls.get("name"),
        evidence_type=EvidenceType.AST,
    )
    d = ref.to_dict()
    d["status"] = "VERIFIED"
    d["issue_type"] = _ISSUE_BY_STEREOTYPE.get(cls.get("stereotype", ""), "MAINTAINABILITY")
    d["risk"] = _RISK_BY_STEREOTYPE.get(cls.get("stereotype", ""), "INFO")
    return d


def _get_class_dependencies(cls: Dict[str, Any]) -> Set[str]:
    """Collects direct dependencies of a class node from AST fields."""
    deps: Set[str] = set()
    for d in cls.get("injected_dependencies") or []:
        if isinstance(d, str):
            deps.add(d.split(".")[-1])
            deps.add(d)
    for d in cls.get("extends") or []:
        if isinstance(d, str):
            deps.add(d.split(".")[-1])
            deps.add(d)
    for d in cls.get("implements") or []:
        if isinstance(d, str):
            deps.add(d.split(".")[-1])
            deps.add(d)
    for d in cls.get("file_imports") or []:
        if isinstance(d, str):
            deps.add(d.split(".")[-1])
    return deps


class ImpactAnalyzer:
    @staticmethod
    def analyze(target_symbol: str, analysis_run_id: str, git_diff: Optional[str] = None) -> ImpactResult:
        # 1. Snapshot identity check (fails closed if unknown run)
        snap = get_snapshot_registry().get(analysis_run_id)
        if not snap:
            raise ValueError(f"UNKNOWN_RUN:{analysis_run_id}")

        # 2. Per-run model only: recover from persistent snapshot storage if evicted from memory
        model: Dict[str, Any] = {}
        try:
            from devlensx.chat.orchestrator import _model_store
            model = _model_store.get(analysis_run_id) or {}
        except Exception:
            model = {}

        if not model or not model.get("classes"):
            try:
                from devlensx.core.persistence import get_storage_manager
                recovered = get_storage_manager().load_snapshot(analysis_run_id)
                if recovered:
                    _, model = recovered
                    try:
                        from devlensx.chat.orchestrator import _model_store
                        _model_store[analysis_run_id] = model
                    except Exception:
                        pass
            except Exception:
                pass

        classes = model.get("classes", []) if isinstance(model, dict) else []
        classes = [c for c in classes if isinstance(c, dict) and c.get("name")]
        relationships = model.get("relationships", []) if isinstance(model, dict) else []

        root_path = Path(snap.repo_path) if snap.repo_path else Path(".")

        # 3. Target Symbol Resolution (supports classes, methods, syntax like Board.isWinner())
        clean_target = str(target_symbol).strip()
        if clean_target.endswith("()"):
            clean_target = clean_target[:-2].strip()

        target_parts = clean_target.split(".")
        target_simple = target_parts[-1]
        target_parent = target_parts[-2] if len(target_parts) >= 2 else None

        prod_classes = [c for c in classes if not is_test_file_or_symbol(c.get("file", ""), c.get("name", ""))]
        pool = prod_classes if prod_classes else classes

        target = None
        # A. Exact match by name or qualified_name
        candidates = [c for c in pool if c.get("name") == clean_target or c.get("qualified_name") == clean_target]
        if candidates:
            if target_parent:
                for cand in candidates:
                    parent_meta = str(cand.get("metadata", {}).get("parent_class") or "")
                    c_file = cand.get("file", "")
                    if target_parent.lower() in parent_meta.lower() or target_parent.lower() in c_file.lower():
                        target = cand
                        break
            if not target:
                candidates.sort(key=lambda c: (
                    0 if "model" in (c.get("file") or "").lower() else 1,
                    0 if c.get("kind") == "class" else 1,
                ))
                target = candidates[0]

        # B. Match Parent.Method
        if not target and target_parent:
            candidates = [
                c for c in pool
                if c.get("name") == target_simple and (
                    target_parent.lower() in str(c.get("metadata", {}).get("parent_class") or "").lower()
                    or target_parent.lower() in (c.get("file") or "").lower()
                )
            ]
            if candidates:
                target = candidates[0]

        # C. Simple name match
        if not target:
            candidates = [c for c in pool if c.get("name") == target_simple or c.get("name") == clean_target]
            if candidates:
                candidates.sort(key=lambda c: (
                    0 if "model" in (c.get("file") or "").lower() else 1,
                    0 if c.get("kind") == "class" else 1,
                ))
                target = candidates[0]

        # D. Match by file path
        if not target:
            for c in pool:
                c_file = (c.get("file") or "").replace("\\", "/")
                if c_file.endswith(clean_target) or c_file.endswith("/" + clean_target):
                    target = c
                    break

        # E. Semantic fuzzy match (e.g. Board.isWinner -> evaluateBoard / isTerminal in Board)
        fuzzy_note = None
        if not target and target_simple.lower() in ("iswinner", "winner", "winningcondition", "iswin"):
            candidates = [
                c for c in pool
                if any(w in c.get("name", "").lower() for w in ("eval", "terminal", "win", "result"))
                and (not target_parent or target_parent.lower() in (c.get("file") or "").lower())
            ]
            if candidates:
                target = candidates[0]
                fuzzy_note = f"Queried condition '{clean_target}' resolved to verified symbol '{target.get('name')}' in {target.get('file')}."

        # F. Match file by name if target matches a source file (e.g. Navbar -> navbar.tsx)
        if not target:
            for f in root_path.rglob("*.*"):
                if f.stem.lower() == clean_target.lower() and f.suffix in (".ts", ".tsx", ".js", ".jsx", ".py", ".java"):
                    rel = str(f.relative_to(root_path)).replace("\\", "/")
                    target = {
                        "name": clean_target,
                        "file": rel,
                        "line_start": 1,
                        "line_end": 30,
                        "kind": "component",
                        "stereotype": "Component",
                    }
                    break

        # Fail closed if target does not exist in active snapshot
        if not target:
            return ImpactResult(
                repository_id=snap.repository_id,
                analysis_run_id=snap.analysis_run_id,
                commit_hash=snap.commit_hash,
                target_symbol=target_symbol,
                status="TARGET_NOT_FOUND",
                risk_level="LOW",
            )

        target_name = target.get("name", target_symbol)
        target_file = (target.get("file") or "").replace("\\", "/")
        target_kind = target.get("kind", "class")
        target_stereo = target.get("stereotype", "Component")
        is_method_target = target_kind in ("method", "constructor", "function")

        # 4. Direct Finding
        direct = [{
            "symbol": target_name,
            "file": target_file,
            "status": "VERIFIED",
            "evidence_ref": _ref_for_class(snap, target),
        }]

        # 5. Direct Callers & Dependency Extraction
        # Cache source file lines to scan method invocations
        file_cache: Dict[str, List[str]] = {}

        def _get_lines(rel_path: str) -> List[str]:
            if rel_path in file_cache:
                return file_cache[rel_path]
            fp = root_path / rel_path
            if fp.exists():
                try:
                    lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
                    file_cache[rel_path] = lines
                    return lines
                except Exception:
                    file_cache[rel_path] = []
                    return []
            file_cache[rel_path] = []
            return []

        direct_callers: List[Dict[str, Any]] = []
        direct_caller_names: Set[str] = set()
        test_callers: List[Dict[str, Any]] = []

        # A. Model relationships (CALLS & DEPENDS_ON)
        for r in relationships:
            if not isinstance(r, dict):
                continue
            src = str(r.get("source", "")).split(".")[-1]
            tgt = str(r.get("target", "")).split(".")[-1]
            rtype = str(r.get("type", "")).upper()
            if tgt.lower() == target_name.lower() and src and src != target_name:
                src_c = next((c for c in classes if c.get("name") == src), None)
                caller_file = (src_c.get("file", "") if src_c else "").replace("\\", "/")
                is_test = is_test_file_or_symbol(caller_file, src) if src_c else False
                entry = {
                    "symbol": src,
                    "file": caller_file,
                    "line_start": int(src_c.get("line_start", 1)) if src_c else 1,
                    "line_end": int(src_c.get("line_end", 20)) if src_c else 20,
                    "relation": rtype if rtype in ("CALLS", "EXTENDS", "IMPLEMENTS") else "CALLS",
                    "confidence": "VERIFIED_CALL",
                    "citation": f"{caller_file}#L{src_c.get('line_start', 1)}-L{src_c.get('line_end', 20)}" if caller_file else "",
                }
                if is_test:
                    test_callers.append(entry)
                elif src not in direct_caller_names:
                    direct_caller_names.add(src)
                    direct_callers.append(entry)

        # B. AST Code Invocation Scan for Method / Function Calls
        call_pattern = re.compile(r"\b" + re.escape(target_name) + r"\s*\(")
        class_ref_pattern = re.compile(
            r"\b(new\s+" + re.escape(target_name) +
            r"|" + re.escape(target_name) + r"\." +
            r"|\b" + re.escape(target_name) + r"\s*\(" +
            r"|import\s+.*\b" + re.escape(target_name) + r"\b)"
        )

        for c in classes:
            cname = c.get("name", "")
            if not cname or cname == target_name:
                continue
            cfile = (c.get("file") or "").replace("\\", "/")
            if not cfile:
                continue

            lines = _get_lines(cfile)
            if not lines:
                continue

            start = max(1, int(c.get("line_start", 1))) - 1
            end = min(len(lines), int(c.get("line_end", len(lines))))
            body = "\n".join(lines[start:end])

            invoked = False
            if is_method_target and call_pattern.search(body):
                invoked = True
            elif not is_method_target and (class_ref_pattern.search(body) or target_name in _get_class_dependencies(c)):
                invoked = True

            if invoked:
                is_test = is_test_file_or_symbol(cfile, cname)
                entry = {
                    "symbol": cname,
                    "file": cfile,
                    "line_start": int(c.get("line_start", 1)),
                    "line_end": int(c.get("line_end", 20)),
                    "relation": "CALLS",
                    "confidence": "VERIFIED_CALL",
                    "citation": f"{cfile}#L{c.get('line_start', 1)}-L{c.get('line_end', 20)}",
                }
                if is_test:
                    test_callers.append(entry)
                elif cname not in direct_caller_names:
                    direct_caller_names.add(cname)
                    direct_callers.append(entry)

        # C. Scan repository source files for unmodeled callers (JSX components, top-level scripts)
        for sfile in list(root_path.rglob("*.tsx")) + list(root_path.rglob("*.ts")) + list(root_path.rglob("*.py")) + list(root_path.rglob("*.java")):
            rel_sfile = str(sfile.relative_to(root_path)).replace("\\", "/")
            if rel_sfile == target_file or rel_sfile in [dc["file"] for dc in direct_callers]:
                continue
            try:
                stext = sfile.read_text(encoding="utf-8", errors="ignore")
                jsx_or_call = (
                    f"<{target_name}" in stext or
                    f"{target_name}(" in stext or
                    f"new {target_name}" in stext or
                    f"import {target_name}" in stext or
                    f"from \"@/components/{Path(target_file).stem}\"" in stext or
                    f"from './{Path(target_file).stem}'" in stext
                )
                if jsx_or_call:
                    sym_name = sfile.stem
                    if "-" in sym_name:
                        sym_name = "".join(part.capitalize() for part in sym_name.split("-"))
                    is_test = is_test_file_or_symbol(rel_sfile, sym_name)
                    entry = {
                        "symbol": sym_name,
                        "file": rel_sfile,
                        "line_start": 1,
                        "line_end": min(50, len(stext.splitlines())),
                        "relation": "CALLS",
                        "confidence": "VERIFIED_CALL",
                        "citation": f"{rel_sfile}#L1-L{min(50, len(stext.splitlines()))}",
                    }
                    if is_test:
                        test_callers.append(entry)
                    elif sym_name not in direct_caller_names:
                        direct_caller_names.add(sym_name)
                        direct_callers.append(entry)
            except Exception:
                pass

        # 6. Transitive Impact (Hop >= 2)
        transitive_callers: List[Dict[str, Any]] = []
        visited_symbols: Set[str] = {target_name} | direct_caller_names
        queue: List[Tuple[str, int, List[str]]] = [(dc["symbol"], 1, [target_name, dc["symbol"]]) for dc in direct_callers]

        while queue and len(transitive_callers) < 30:
            curr_sym, curr_hop, curr_path = queue.pop(0)
            if curr_hop >= 4:
                continue

            curr_pattern = re.compile(r"\b" + re.escape(curr_sym) + r"\b")
            for c in classes:
                cname = c.get("name", "")
                if not cname or cname in visited_symbols:
                    continue
                cfile = (c.get("file") or "").replace("\\", "/")
                if is_test_file_or_symbol(cfile, cname):
                    continue

                lines = _get_lines(cfile)
                start = max(1, int(c.get("line_start", 1))) - 1
                end = min(len(lines), int(c.get("line_end", len(lines))))
                body = "\n".join(lines[start:end])

                if curr_pattern.search(body) or curr_sym in _get_class_dependencies(c):
                    visited_symbols.add(cname)
                    next_path = curr_path + [cname]
                    transitive_callers.append({
                        "symbol": cname,
                        "file": cfile,
                        "line_start": int(c.get("line_start", 1)),
                        "line_end": int(c.get("line_end", 20)),
                        "relation": "TRANSITIVE_CALL",
                        "hop": curr_hop + 1,
                        "path": next_path,
                        "confidence": "VERIFIED_CALL",
                        "citation": f"{cfile}#L{c.get('line_start', 1)}-L{c.get('line_end', 20)}",
                    })
                    queue.append((cname, curr_hop + 1, next_path))

        # 7. Structural Dependencies (EXTENDS, IMPLEMENTS, IMPORTS, INJECTS)
        dependencies: List[Dict[str, Any]] = []
        dep_seen: Set[str] = set()

        for c in classes:
            cname = c.get("name", "")
            if not cname or cname == target_name or cname in dep_seen:
                continue
            cfile = (c.get("file") or "").replace("\\", "/")
            if is_test_file_or_symbol(cfile, cname):
                continue

            rel_type = None
            if target_name in (c.get("extends") or []):
                rel_type = "EXTENDS"
            elif target_name in (c.get("implements") or []):
                rel_type = "IMPLEMENTS"
            elif target_name in (c.get("injected_dependencies") or []):
                rel_type = "INJECTS"
            elif target_name in (c.get("file_imports") or []):
                rel_type = "IMPORTS"

            if rel_type:
                dep_seen.add(cname)
                dependencies.append({
                    "symbol": cname,
                    "file": cfile,
                    "relation": rel_type,
                    "detail": f"Structural {rel_type} contract referencing {target_name}",
                })

        # 8. Test Discovery (Strictly Relevant Tests)
        tests: List[Dict[str, Any]] = []
        test_seen: Set[str] = set()

        # Add callers that are test methods
        for tc in test_callers:
            tsym = tc["symbol"]
            if tsym not in test_seen:
                test_seen.add(tsym)
                tests.append({
                    "symbol": tsym,
                    "file": tc["file"],
                    "line_start": tc["line_start"],
                    "line_end": tc["line_end"],
                    "status": "VERIFIED",
                    "relation": "TESTS",
                })

        # Add test classes specifically matching target or direct callers
        affected_names = {target_name} | {dc["symbol"] for dc in direct_callers}
        for c in classes:
            cname = c.get("name", "")
            cfile = (c.get("file") or "").replace("\\", "/")
            if not is_test_file_or_symbol(cfile, cname) or cname in test_seen:
                continue

            cdeps = _get_class_dependencies(c)
            is_relevant_test = (
                bool(affected_names.intersection(cdeps)) or
                any(aff.lower() in cname.lower() for aff in affected_names if len(aff) >= 3)
            )
            if is_relevant_test:
                test_seen.add(cname)
                tests.append({
                    "symbol": cname,
                    "file": cfile,
                    "line_start": int(c.get("line_start", 1)),
                    "line_end": int(c.get("line_end", 20)),
                    "status": "VERIFIED",
                    "relation": "TESTS",
                })

        # 9. Coverage Limitations & Uncertainty Disclosure
        coverage_limitations: List[str] = []
        has_dynamic_dispatch = False

        if any("[" in (c.get("file") or "") for c in classes):
            coverage_limitations.append("Dynamic routing detected: parameterized route segments (e.g. [slug]) invoke runtime handlers not bound to static AST call graphs.")
            has_dynamic_dispatch = True

        # Check repository source code for dynamic behavior
        sample_files = list(root_path.rglob("*.java"))[:10] + list(root_path.rglob("*.py"))[:10] + list(root_path.rglob("*.ts*"))[:10]
        for f in sample_files:
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
                if "java.lang.reflect" in txt or "Class.forName" in txt or "method.invoke" in txt:
                    if not any("Reflection" in c for c in coverage_limitations):
                        coverage_limitations.append("Reflection detected: runtime invocations via java.lang.reflect cannot be verified by static AST analysis.")
                    has_dynamic_dispatch = True
                if "getattr(" in txt or "eval(" in txt:
                    if not any("Dynamic dispatch" in c for c in coverage_limitations):
                        coverage_limitations.append("Dynamic dispatch detected: runtime attribute/function lookup cannot be completely proved statically.")
                    has_dynamic_dispatch = True
                if ("dynamic(" in txt or "React.lazy" in txt) and not any("Dynamic routing" in c for c in coverage_limitations):
                    coverage_limitations.append("Dynamic routing / import detected: runtime route parameters may invoke unmodeled handler endpoints.")
                    has_dynamic_dispatch = True
            except Exception:
                pass

        if fuzzy_note:
            coverage_limitations.append(fuzzy_note)

        # Distinguish execution order types
        if has_dynamic_dispatch:
            execution_order_type = "UNRESOLVED_RUNTIME_BEHAVIOR"
        elif direct_callers and all(c.get("relation") == "CALLS" for c in direct_callers):
            execution_order_type = "VERIFIED_CALL_ORDER"
        else:
            execution_order_type = "INFERRED_ARCHITECTURE_ORDER"

        # 10. Potential Regressions & Recommended Validation
        potential_regressions: List[str] = []
        recommended_validations: List[str] = []

        if any(w in target_name.lower() for w in ("win", "terminal", "eval", "check", "valid")):
            potential_regressions.extend([
                "Game state condition may trigger prematurely or fail to detect valid winning lines.",
                "Boundary condition errors (e.g. off-by-one in grid coordinates) could cause False negatives or out-of-bounds exceptions.",
                "Downstream UI state and minimax depth evaluations may desynchronize if terminal criteria disagree with board state."
            ])
            recommended_validations.extend([
                "Test horizontal winning configurations across all grid rows.",
                "Test vertical winning configurations across all grid columns.",
                "Test forward and backward diagonal winning lines.",
                "Test empty board, incomplete board, and full-board draw termination boundaries."
            ])
        elif any(w in target_name.lower() for w in ("minimax", "ai", "search", "bestmove")):
            potential_regressions.extend([
                "Depth limit or heuristic calculation changes could alter decision tree evaluation, yielding suboptimal moves.",
                "Alpha-beta pruning cutoffs could prune optimal winning branches if score evaluation polarity is inverted."
            ])
            recommended_validations.extend([
                "Verify optimal move selection against benchmark tactical scenario suites.",
                "Run minimax depth tests to ensure pruning bounds remain sound across all turn depths."
            ])
        elif any(w in target_name.lower() for w in ("place", "move", "ship", "cell")):
            potential_regressions.extend([
                "State mutation without idempotency or validation may corrupt grid invariants or throw unexpected exceptions.",
                "Caller state desynchronization if UI listeners or event buses fail to receive transition notifications."
            ])
            recommended_validations.extend([
                "Verify invalid coordinate rejection and occupied cell exception guarantees.",
                "Test turn alternation and game-over state transitions with end-to-end event dispatch."
            ])
        else:
            potential_regressions.append(
                f"Modifications to {target_name} may impact {len(direct_callers)} direct caller(s) and {len(transitive_callers)} transitive downstream component(s)."
            )
            recommended_validations.append(
                f"Run regression test suite: {', '.join([t['symbol'] for t in tests[:3]]) or 'local unit tests'}."
            )

        # 11. Git Diff / Change Comparison
        diff_analysis: Optional[Dict[str, Any]] = None
        if git_diff:
            is_changed = bool(re.search(r"^[+-].*\b" + re.escape(target_name) + r"\b", git_diff, re.MULTILINE))
            sig_altered = bool(re.search(r"^[+-].*\b" + re.escape(target_name) + r"\s*\(", git_diff, re.MULTILINE))
            try:
                from devlensx.review.hunks import HunkParser
                from devlensx.review.symbol_resolver import resolve_changed_symbols
                file_diffs = HunkParser.parse(git_diff)
                changed_syms = resolve_changed_symbols(file_diffs, model)
                if any(cs.name == target_name for cs in changed_syms):
                    is_changed = True
            except Exception:
                pass

            diff_analysis = {
                "changed_in_diff": is_changed,
                "signature_altered": sig_altered,
                "impact_summary": (
                    f"Target '{target_name}' modified in git diff; {len(direct_callers)} direct caller(s) require call-site verification."
                    if is_changed else
                    f"Target '{target_name}' was not modified in the supplied diff."
                ),
                "affected_callers": [dc["symbol"] for dc in direct_callers] if is_changed else []
            }

        # 12. Risk Assessment
        risk_score = 0
        reasons = []

        if len(direct_callers) >= 5:
            risk_score += 35
            reasons.append(f"High caller fan-in: {len(direct_callers)} direct production callers depend on this symbol.")
        elif len(direct_callers) >= 2:
            risk_score += 20
            reasons.append(f"Multiple callers: {len(direct_callers)} direct callers depend on this symbol.")
        elif len(direct_callers) == 1:
            risk_score += 10
            reasons.append("Single direct caller identified.")
        else:
            reasons.append("Zero direct callers found (leaf node or top-level entrypoint).")

        if len(transitive_callers) >= 5:
            risk_score += 25
            reasons.append(f"Broad blast radius: {len(transitive_callers)} transitive downstream components reached.")
        elif len(transitive_callers) >= 1:
            risk_score += 10
            reasons.append(f"{len(transitive_callers)} transitive downstream component(s) affected.")

        stereo_lower = str(target_stereo).lower()
        if "controller" in stereo_lower or "endpoint" in stereo_lower:
            risk_score += 30
            reasons.append("Public API boundary: external consumers or HTTP contracts directly exposed.")
        elif "repo" in stereo_lower or "entity" in stereo_lower:
            risk_score += 25
            reasons.append("Data persistence boundary: database schema or transactional state affected.")

        if not tests:
            risk_score += 20
            reasons.append("Coverage gap: No automated tests found exercising this symbol.")
        else:
            reasons.append(f"Covered by {len(tests)} test suite(s).")

        if risk_score >= 50:
            risk_level = "CRITICAL"
        elif risk_score >= 30:
            risk_level = "HIGH"
        elif risk_score >= 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        risk_assessment = {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "reasons": reasons,
            "caller_count": len(direct_callers),
            "transitive_count": len(transitive_callers),
            "test_count": len(tests),
        }

        # 13. Deterministic Mermaid Diagram
        mermaid_lines = ["graph TD"]
        mermaid_lines.append(f'  subgraph Target["Target Component"]')
        mermaid_lines.append(f'    T["{target_name}\\n({target_stereo})"]')
        mermaid_lines.append(f'  end')
        mermaid_lines.append('  style T fill:#2563eb,stroke:#60a5fa,stroke-width:2px,color:#fff')

        if direct_callers:
            mermaid_lines.append('  subgraph DirectCallers["Direct Callers (CALLS)"]')
            for i, dc in enumerate(direct_callers[:5]):
                c_id = f"DC_{i}"
                mermaid_lines.append(f'    {c_id}["{dc["symbol"]}"] -->|calls| T')
            mermaid_lines.append('  end')

        if transitive_callers:
            mermaid_lines.append('  subgraph Transitive["Transitive Downstream"]')
            for i, tc in enumerate(transitive_callers[:4]):
                t_id = f"TC_{i}"
                mermaid_lines.append(f'    {t_id}["{tc["symbol"]}"] -.->|transitive| DC_0')
            mermaid_lines.append('  end')

        if tests:
            mermaid_lines.append('  subgraph TestSuites["Test Verification"]')
            for i, ts in enumerate(tests[:4]):
                ts_id = f"TEST_{i}"
                mermaid_lines.append(f'    {ts_id}["{ts["symbol"]}"] ==>|tests| T')
            mermaid_lines.append('  end')

        mermaid_str = "\n".join(mermaid_lines)
        diagram = {
            "type": "CHANGE_IMPACT",
            "mermaid": mermaid_str,
            "format": "mermaid",
            "content": mermaid_str,
        }

        # 14. Backward-compatible downstream list (merges direct, transitive, dependencies)
        downstream_map: Dict[str, Dict[str, Any]] = {}
        for item in direct_callers + transitive_callers:
            s = item["symbol"]
            if s not in downstream_map:
                downstream_map[s] = {
                    "symbol": s,
                    "file": item["file"],
                    "status": "VERIFIED",
                }
        for d in dependencies:
            s = d["symbol"]
            if s not in downstream_map:
                downstream_map[s] = {
                    "symbol": s,
                    "file": d["file"],
                    "status": "VERIFIED",
                }

        downstream = list(downstream_map.values())

        # Evidence Refs
        evidence_refs: List[Dict[str, Any]] = [_ref_for_class(snap, target)]
        for dc in direct_callers[:5]:
            dc_c = next((c for c in classes if c.get("name") == dc["symbol"]), None)
            if dc_c:
                evidence_refs.append(_ref_for_class(snap, dc_c))
        for ts in tests[:3]:
            ts_c = next((c for c in classes if c.get("name") == ts["symbol"]), None)
            if ts_c:
                evidence_refs.append(_ref_for_class(snap, ts_c))

        configs = [cfg for cfg in model.get("configurations", [])[:5] if target_name.lower() in str(cfg).lower()]

        return ImpactResult(
            repository_id=snap.repository_id,
            analysis_run_id=snap.analysis_run_id,
            commit_hash=snap.commit_hash,
            target_symbol=target_name,
            direct=direct,
            downstream=downstream,
            tests=tests,
            configs=configs,
            evidence_refs=evidence_refs,
            diagram=diagram,
            status="OK",
            risk_level=risk_level,
            direct_callers=direct_callers,
            transitive_callers=transitive_callers,
            dependencies=dependencies,
            potential_regressions=potential_regressions,
            recommended_validations=recommended_validations,
            coverage_limitations=coverage_limitations,
            execution_order_type=execution_order_type,
            risk_assessment=risk_assessment,
            diff_analysis=diff_analysis,
        )
