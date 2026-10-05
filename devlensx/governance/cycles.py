"""
DevLensX Architectural Cycle Detection Engine (Phase P5-A)

Explicitly distinguishes and detects:
1. IMPORT_CYCLE: Circular import chains between modules/packages.
2. INHERITANCE_CYCLE: Circular inheritance / implementation loops.
3. CALL_GRAPH_CYCLE: Cross-component circular recursive invocation sequences.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Set, Tuple
from devlensx.governance.models import CycleType, CandidateViolation
from devlensx.evidence.models import EvidenceRef, EvidenceType


def find_directed_cycles(adj: Dict[str, List[str]]) -> List[List[str]]:
    """
    Finds elementary directed cycles in a graph represented as adjacency list.
    Deduplicates rotated cycles so that each unique cycle is reported once,
    with the lexicographically lowest node first, ending with that same node.
    """
    visited: Set[str] = set()
    rec_stack: Dict[str, int] = {}
    current_path: List[str] = []
    found_cycles: List[List[str]] = []
    seen_cycle_signatures: Set[Tuple[str, ...]] = set()

    def dfs(node: str):
        visited.add(node)
        rec_stack[node] = len(current_path)
        current_path.append(node)

        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Cycle detected
                cycle_slice = current_path[rec_stack[neighbor]:]
                if len(cycle_slice) >= 1:
                    # Canonical rotation to deduplicate
                    min_idx = cycle_slice.index(min(cycle_slice))
                    canonical = cycle_slice[min_idx:] + cycle_slice[:min_idx]
                    canonical_tuple = tuple(canonical)
                    if canonical_tuple not in seen_cycle_signatures:
                        seen_cycle_signatures.add(canonical_tuple)
                        found_cycles.append(canonical + [canonical[0]])

        current_path.pop()
        del rec_stack[node]

    for start_node in list(adj.keys()):
        if start_node not in visited:
            dfs(start_node)

    return found_cycles


def detect_import_cycles(
    classes: List[Dict[str, Any]],
    snapshot_identity: Tuple[str, str, Optional[str]],
    file_imports: Optional[Dict[str, List[str]]] = None,
) -> List[CandidateViolation]:
    """
    Detects circular module/package imports.
    Builds module dependency graph from class package/imports or explicit file_imports.
    """
    repo_id, run_id, commit_hash = snapshot_identity
    adj: Dict[str, List[str]] = {}
    symbol_file_map: Dict[str, Tuple[str, int, int]] = {}

    # 1. From explicit file_imports if available
    if file_imports:
        for src_file, imports in file_imports.items():
            adj.setdefault(src_file, [])
            for imp in imports:
                adj[src_file].append(imp)
                adj.setdefault(imp, [])
            symbol_file_map[src_file] = (src_file, 1, 1)

    # 2. From class symbol imports & packages
    for cls in classes:
        cls_name = cls.get("name", "")
        file_path = cls.get("file") or cls.get("file_path") or f"{cls_name}.java"
        line_start = int(cls.get("line_start") or 1)
        line_end = int(cls.get("line_end") or line_start + 10)
        symbol_file_map[cls_name] = (file_path, line_start, line_end)

        cls_imports = cls.get("imports") or (cls.get("metadata") or {}).get("imports") or []
        src_module = cls.get("package") or file_path.rsplit(".", 1)[0]
        adj.setdefault(src_module, [])
        symbol_file_map.setdefault(src_module, (file_path, line_start, line_end))

        for imp in cls_imports:
            imp_mod = str(imp).rsplit(".", 1)[0]
            if imp_mod and imp_mod != src_module:
                adj[src_module].append(imp_mod)
                adj.setdefault(imp_mod, [])

    raw_cycles = find_directed_cycles(adj)
    violations: List[CandidateViolation] = []

    for cycle in raw_cycles:
        # Filter trivial self-loops unless desired
        if len(cycle) <= 2:
            continue
        first_node = cycle[0]
        fpath, lstart, lend = symbol_file_map.get(first_node, (f"{first_node}.py", 1, 10))
        cycle_str = " -> ".join(cycle)
        
        evidence_ref = EvidenceRef(
            repository_id=repo_id,
            analysis_run_id=run_id,
            commit_hash=commit_hash,
            file_path=fpath,
            line_start=lstart,
            line_end=lend,
            symbol_name=first_node,
            evidence_type=EvidenceType.AST,
        )

        violations.append(CandidateViolation(
            rule_id="ARCH-003-IMPORT",
            violation_type=CycleType.IMPORT_CYCLE.value,
            severity="WARNING",
            source_symbol=first_node,
            target_symbol=cycle[1] if len(cycle) > 1 else None,
            file_path=fpath,
            line_start=lstart,
            line_end=lend,
            evidence_ref=evidence_ref,
            description=f"Circular module import chain detected: {cycle_str}",
            metadata={"cycle_path": cycle, "cycle_type": CycleType.IMPORT_CYCLE.value},
        ))

    return violations


def detect_inheritance_cycles(
    classes: List[Dict[str, Any]],
    snapshot_identity: Tuple[str, str, Optional[str]],
    graph_edges: Optional[List[Dict[str, Any]]] = None,
) -> List[CandidateViolation]:
    """
    Detects circular class inheritance loops (Class A extends Class B extends Class A).
    """
    repo_id, run_id, commit_hash = snapshot_identity
    adj: Dict[str, List[str]] = {}
    symbol_file_map: Dict[str, Tuple[str, int, int]] = {}

    for cls in classes:
        name = cls.get("name", "")
        file_path = cls.get("file") or cls.get("file_path") or f"{name}.java"
        line_start = int(cls.get("line_start") or 1)
        line_end = int(cls.get("line_end") or line_start + 10)
        symbol_file_map[name] = (file_path, line_start, line_end)
        adj.setdefault(name, [])

        parents = list(cls.get("extends") or []) + list(cls.get("implements") or [])
        meta = cls.get("metadata") or {}
        parents += list(meta.get("extends") or []) + list(meta.get("implements") or [])

        for p in parents:
            p_name = str(p).split(".")[-1]
            if p_name and p_name != name:
                adj[name].append(p_name)
                adj.setdefault(p_name, [])

    # Also incorporate graph edges typed EXTENDS/IMPLEMENTS
    if graph_edges:
        for e in graph_edges:
            edge_type = str(e.get("type", "")).upper()
            if edge_type in ("EXTENDS", "IMPLEMENTS", "INHERITS"):
                src = str(e.get("source") or e.get("subject") or "").split(".")[-1]
                tgt = str(e.get("target") or e.get("object") or "").split(".")[-1]
                if src and tgt and src != tgt:
                    adj.setdefault(src, []).append(tgt)
                    adj.setdefault(tgt, [])

    raw_cycles = find_directed_cycles(adj)
    violations: List[CandidateViolation] = []

    for cycle in raw_cycles:
        if len(cycle) <= 2:
            continue
        first_node = cycle[0]
        fpath, lstart, lend = symbol_file_map.get(first_node, (f"{first_node}.java", 1, 10))
        cycle_str = " -> ".join(cycle)

        evidence_ref = EvidenceRef(
            repository_id=repo_id,
            analysis_run_id=run_id,
            commit_hash=commit_hash,
            file_path=fpath,
            line_start=lstart,
            line_end=lend,
            symbol_name=first_node,
            evidence_type=EvidenceType.AST,
        )

        violations.append(CandidateViolation(
            rule_id="ARCH-003-INHERITANCE",
            violation_type=CycleType.INHERITANCE_CYCLE.value,
            severity="CRITICAL",
            source_symbol=first_node,
            target_symbol=cycle[1] if len(cycle) > 1 else None,
            file_path=fpath,
            line_start=lstart,
            line_end=lend,
            evidence_ref=evidence_ref,
            description=f"Circular class inheritance loop detected: {cycle_str}",
            metadata={"cycle_path": cycle, "cycle_type": CycleType.INHERITANCE_CYCLE.value},
        ))

    return violations


def detect_call_graph_cycles(
    classes: List[Dict[str, Any]],
    snapshot_identity: Tuple[str, str, Optional[str]],
    graph_edges: Optional[List[Dict[str, Any]]] = None,
) -> List[CandidateViolation]:
    """
    Detects cross-component circular recursive call chains (Component A -> Component B -> Component A).
    Ignores simple intra-method self-recursion, focusing on mutual architectural recursion.
    """
    repo_id, run_id, commit_hash = snapshot_identity
    adj: Dict[str, List[str]] = {}
    symbol_file_map: Dict[str, Tuple[str, int, int]] = {}

    for cls in classes:
        cname = cls.get("name", "")
        fpath = cls.get("file") or cls.get("file_path") or f"{cname}.java"
        lstart = int(cls.get("line_start") or 1)
        lend = int(cls.get("line_end") or lstart + 10)
        symbol_file_map[cname] = (fpath, lstart, lend)
        adj.setdefault(cname, [])

        for dep in cls.get("injected_dependencies", []):
            dname = str(dep).split(".")[-1]
            if dname and dname != cname:
                adj[cname].append(dname)
                adj.setdefault(dname, [])

    if graph_edges:
        for e in graph_edges:
            etype = str(e.get("type", "")).upper()
            if etype in ("CALLS", "INVOKES", "USES", "DEPENDS_ON"):
                src = str(e.get("source") or e.get("subject") or "").split(".")[-1]
                tgt = str(e.get("target") or e.get("object") or "").split(".")[-1]
                if src and tgt and src != tgt:
                    adj.setdefault(src, []).append(tgt)
                    adj.setdefault(tgt, [])

    raw_cycles = find_directed_cycles(adj)
    violations: List[CandidateViolation] = []

    for cycle in raw_cycles:
        if len(cycle) <= 2:
            continue
        first_node = cycle[0]
        fpath, lstart, lend = symbol_file_map.get(first_node, (f"{first_node}.java", 1, 10))
        cycle_str = " -> ".join(cycle)

        evidence_ref = EvidenceRef(
            repository_id=repo_id,
            analysis_run_id=run_id,
            commit_hash=commit_hash,
            file_path=fpath,
            line_start=lstart,
            line_end=lend,
            symbol_name=first_node,
            evidence_type=EvidenceType.GRAPH,
        )

        violations.append(CandidateViolation(
            rule_id="ARCH-003-CALL",
            violation_type=CycleType.CALL_GRAPH_CYCLE.value,
            severity="WARNING",
            source_symbol=first_node,
            target_symbol=cycle[1] if len(cycle) > 1 else None,
            file_path=fpath,
            line_start=lstart,
            line_end=lend,
            evidence_ref=evidence_ref,
            description=f"Cross-component circular call recursion detected: {cycle_str}",
            metadata={"cycle_path": cycle, "cycle_type": CycleType.CALL_GRAPH_CYCLE.value},
        ))

    return violations
