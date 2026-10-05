"""P1-C review grounding orchestration.

Pipeline:
  diff -> HunkParser -> ChangedSymbol (range containment)
       -> base-commit compatibility (EXACT_SNAPSHOT | BASE_MISMATCH | UNKNOWN_BASE)
       -> affected-set resolution (Kuzu hop-1 + model edges, BFS to MAX_IMPACT_HOPS)
       -> deterministic Mermaid change diagram
       -> evidence assembly (snapshot-bound EvidenceRefs)

Rules:
- The affected set NEVER comes from the LLM — only Kuzu/model traversal.
- Graph hits outside the requested snapshot's model are dropped (the Kuzu
  store is process-global; isolation is enforced here by intersection).
- BASE_MISMATCH downgrades changed-line refs to declaration spans and is
  reported explicitly — never silently treated as exact.
- Centrality/fan-in may rank, never verify (no VERIFIED findings created here).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from devlensx.core.config import (
    MAX_AFFECTED_PER_SYMBOL,
    MAX_AFFECTED_TOTAL,
    MAX_IMPACT_HOPS,
    MAX_MERMAID_NODES,
)
from devlensx.review.hunks import HunkParser, ParseResult
from devlensx.review.symbol_resolver import resolve_changed_symbols, ChangedSymbol, summarize
from devlensx.evidence.models import EvidenceRef, EvidenceType


# ---------------------------------------------------------------------------
# Base-commit compatibility
# ---------------------------------------------------------------------------
EXACT_SNAPSHOT = "EXACT_SNAPSHOT"
BASE_MISMATCH = "BASE_MISMATCH"
UNKNOWN_BASE = "UNKNOWN_BASE"


def check_base_compat(
    base_commit: Optional[str],
    snapshot: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare the diff's base commit against the snapshot commit.

    - base None/empty -> UNKNOWN_BASE (allowed, flagged unverified base).
    - snapshot without commit -> UNKNOWN_BASE.
    - equal (prefix-tolerant) -> EXACT_SNAPSHOT.
    - otherwise -> BASE_MISMATCH (changed-line grounding downgraded).
    """
    snap_commit = (snapshot or {}).get("commit_hash")
    if not base_commit or not snap_commit:
        return {
            "status": UNKNOWN_BASE,
            "detail": "Diff base commit not supplied or snapshot has no commit; "
                      "line grounding flagged as base-unverified.",
        }
    b, s = str(base_commit).strip(), str(snap_commit).strip()
    if b == s or s.startswith(b) or b.startswith(s):
        return {"status": EXACT_SNAPSHOT, "detail": "Diff base matches snapshot commit."}
    return {
        "status": BASE_MISMATCH,
        "detail": f"Diff base {b[:12]} != snapshot commit {s[:12]}; "
                  "changed-line ranges downgraded to declaration spans.",
    }


# ---------------------------------------------------------------------------
# Affected-set resolution
# ---------------------------------------------------------------------------
def _token_match(haystack: str, needle: str) -> bool:
    import re
    if not haystack or not needle:
        return False
    return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None


def _model_edges(model: Dict[str, Any]) -> Dict[str, List[Tuple[str, str]]]:
    """dependent -> [(relationship, target)] from model relationships + injections."""
    from devlensx.deep_reasoning import simple_name
    adj: Dict[str, List[Tuple[str, str]]] = {}
    for r in (model or {}).get("relationships", []) or []:
        if not isinstance(r, dict):
            continue
        src, tgt = simple_name(r.get("source", "")), simple_name(r.get("target", ""))
        if src and tgt and src != tgt:
            adj.setdefault(src, []).append(("DEPENDS_ON", tgt))
    for c in (model or {}).get("classes", []) or []:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        name = c["name"]
        for dep in (c.get("injected_dependencies") or []):
            tgt = simple_name(dep)
            if tgt and tgt != name:
                adj.setdefault(name, []).append(("INJECTS", tgt))
        for base in (c.get("extends") or []):
            tgt = simple_name(base)
            if tgt and tgt != name:
                adj.setdefault(name, []).append(("EXTENDS", tgt))
        for iface in (c.get("implements") or []):
            tgt = simple_name(iface)
            if tgt and tgt != name:
                adj.setdefault(name, []).append(("IMPLEMENTS", tgt))
    return adj


def _reverse_adj(adj: Dict[str, List[Tuple[str, str]]]) -> Dict[str, List[Tuple[str, str]]]:
    rev: Dict[str, List[Tuple[str, str]]] = {}
    for src, edges in adj.items():
        for rel, tgt in edges:
            rev.setdefault(tgt, []).append((rel, src))
    return rev


def _ref(snapshot: Dict[str, Any], cls: Dict[str, Any]) -> Dict[str, Any]:
    return EvidenceRef(
        repository_id=snapshot.get("repository_id"),
        analysis_run_id=snapshot.get("analysis_run_id"),
        commit_hash=snapshot.get("commit_hash"),
        file_path=(cls.get("file") or "").replace("\\", "/"),
        line_start=int(cls.get("line_start") or 1),
        line_end=int(cls.get("line_end") or 1),
        symbol_name=cls.get("name"),
        evidence_type=EvidenceType.AST,
    ).to_dict()


def _associated_tests(symbol: str, model: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Test nodes referencing the symbol.

    Matches Test<Symbol>, <Symbol>Test, token mentions in the test name, or
    the symbol as a path token in the test file. Deliberately narrower than
    substring soup: "Order" does not match "ReorderTests" (boundary check),
    but "OrderServiceTest" matches scope "OrderService" (prefix convention).
    """
    out = []
    for c in (model or {}).get("classes", []) or []:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "")
        is_test = bool(c.get("is_test")) or c.get("stereotype") == "Test" or "Test" in name
        if not is_test or not symbol:
            continue
        if (name == symbol or name.startswith(symbol)
                or _token_match(name, symbol) or _token_match(c.get("file", ""), symbol)):
            out.append(c)
    return out


def resolve_affected(
    changed: List[ChangedSymbol],
    model: Dict[str, Any],
    snapshot: Dict[str, Any],
    graph_store: Any = None,
    max_hops: int = MAX_IMPACT_HOPS,
) -> List[Dict[str, Any]]:
    """Deterministic affected set for changed symbols.

    Sources: Kuzu hop-1 (intersected with snapshot model) + model-edge BFS.
    Every entry carries relationship, direction, provenance, snapshot refs.
    """
    model = model or {}
    classes = [c for c in model.get("classes", []) if isinstance(c, dict)]
    by_name = {c["name"]: c for c in classes if c.get("name")}
    model_names = set(by_name)

    adj = _model_edges(model)
    rev = _reverse_adj(adj)

    affected: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def emit(symbol: str, relationship: str, source_symbol: str, via: str, hop: int) -> None:
        if symbol in seen or symbol not in model_names:
            return
        if len(affected) >= MAX_AFFECTED_TOTAL:
            return
        seen.add(symbol)
        cls = by_name[symbol]
        affected.append({
            "symbol": symbol,
            "relationship": relationship,      # CALLER_OF | DEPENDENT_OF | IMPLEMENTS | EXTENDS | TESTS
            "source_symbol": source_symbol,   # changed symbol this traces to
            "target_symbol": symbol,
            "via": via,                        # kuzu | model
            "hop": hop,
            "file": cls.get("file", ""),
            "stereotype": cls.get("stereotype", ""),
            "evidence_refs": [_ref(snapshot, cls)],
        })

    for cs in changed:
        per_symbol = 0

        def emit_capped(**kw: Any) -> None:
            nonlocal per_symbol
            if per_symbol >= MAX_AFFECTED_PER_SYMBOL:
                return
            before = len(affected)
            emit(**kw)
            if len(affected) > before:
                per_symbol += 1

        # Hop 1: Kuzu callers/dependents (intersected with snapshot model)
        if graph_store is not None and hasattr(graph_store, "query_change_impact"):
            try:
                for r in graph_store.query_change_impact(cs.name) or []:
                    sym = r.get("caller") or r.get("class_name")
                    if sym and sym != cs.name and sym in model_names:
                        emit_capped(symbol=sym, relationship="CALLER_OF",
                                    source_symbol=cs.name, via="kuzu", hop=1)
            except Exception:
                pass

        # BFS over model edges, both directions:
        # reverse (who depends on / calls X) and forward (what X calls).
        # Hop counts edges from the changed symbol; caps bound explosion.
        frontier = [(cs.name, 0)]
        visited = {cs.name}
        while frontier and per_symbol < MAX_AFFECTED_PER_SYMBOL:
            node, hop = frontier.pop(0)
            if hop >= max_hops:
                continue
            neighbors: List[Tuple[str, str, str]] = []
            for rel, dependent in rev.get(node, []):
                kind = {"INJECTS": "DEPENDENT_OF", "DEPENDS_ON": "DEPENDENT_OF",
                        "EXTENDS": "EXTENDS", "IMPLEMENTS": "IMPLEMENTS"}.get(rel, "DEPENDENT_OF")
                neighbors.append((dependent, kind, "model"))
            for rel, target in adj.get(node, []):
                kind = {"INJECTS": "INJECTS", "DEPENDS_ON": "DEPENDS_ON",
                        "EXTENDS": "EXTENDS", "IMPLEMENTS": "IMPLEMENTS"}.get(rel, "DEPENDS_ON")
                neighbors.append((target, kind, "model"))
            for other, kind, via in neighbors:
                if other in visited or other not in model_names:
                    continue
                visited.add(other)
                emit_capped(symbol=other, relationship=kind,
                            source_symbol=cs.name, via=via, hop=hop + 1)
                frontier.append((other, hop + 1))

        # Associated tests (first-class impact evidence). A changed method
        # implicates its enclosing class's tests too (placeOrder -> OrderServiceTest).
        scope_names = [cs.name] + ([cs.enclosing] if cs.enclosing else [])
        for scope in scope_names:
            for t in _associated_tests(scope, model):
                emit_capped(symbol=t["name"], relationship="TESTS",
                            source_symbol=cs.name, via="model", hop=1)

    return affected


# ---------------------------------------------------------------------------
# Deterministic change diagram (Mermaid from traversed graph only)
# ---------------------------------------------------------------------------
def _mermaid_id(s: str) -> str:
    import re
    clean = re.sub(r"[^A-Za-z0-9_]", "_", str(s or ""))
    if clean and clean[0].isdigit():
        clean = "n_" + clean
    return clean or "node"


def _mermaid_label(s: str) -> str:
    return str(s or "").replace('"', "'").replace("\n", " ")[:60]


def build_change_mermaid(
    changed: List[ChangedSymbol],
    affected: List[Dict[str, Any]],
) -> str:
    """graph TD over changed -> affected edges. No LLM topology."""
    edges: List[Tuple[str, str, str]] = []
    nodes: Dict[str, str] = {}
    changed_names = [c.name for c in changed][:MAX_MERMAID_NODES]
    for n in changed_names:
        nodes[n] = "changed"
    for a in affected:
        src, tgt = a.get("source_symbol", ""), a.get("target_symbol", "")
        if not src or not tgt:
            continue
        if len(nodes) >= MAX_MERMAID_NODES and tgt not in nodes:
            continue
        nodes.setdefault(src, "affected")
        nodes.setdefault(tgt, "affected")
        edges.append((src, tgt, a.get("relationship", "DEPENDS_ON")))
    lines = ["graph TD"]
    for n in sorted(nodes):
        lines.append(f'    {_mermaid_id(n)}["{_mermaid_label(n)}"]')
    for src, tgt, rel in sorted(set(edges)):
        lines.append(f"    {_mermaid_id(src)} -->|{rel}| {_mermaid_id(tgt)}")
    if len(lines) == 1:
        lines.append('    Empty["No affected components"]')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestrator: one call used by ReviewEngine + codereview
# ---------------------------------------------------------------------------
@dataclass
class GroundingResult:
    parsed_files: int = 0
    truncated: bool = False
    changed: List[ChangedSymbol] = field(default_factory=list)
    base_compat: Dict[str, Any] = field(default_factory=dict)
    affected: List[Dict[str, Any]] = field(default_factory=list)
    mermaid: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parsed_files": self.parsed_files,
            "truncated": self.truncated,
            "changed": [c.to_dict() for c in self.changed],
            "base_compat": self.base_compat,
            "affected": self.affected,
            "mermaid": self.mermaid,
            "summary": self.summary,
        }


def ground_diff(
    diff: str,
    model: Dict[str, Any],
    snapshot: Dict[str, Any],
    base_commit: Optional[str] = None,
    graph_store: Any = None,
) -> GroundingResult:
    """Full P1-C grounding: parse -> resolve -> compat -> affected -> diagram."""
    parsed = HunkParser.parse(diff or "")
    changed = resolve_changed_symbols(parsed, model or {})
    compat = check_base_compat(base_commit, snapshot)
    affected = resolve_affected(changed, model or {}, snapshot or {}, graph_store)
    mermaid = build_change_mermaid(changed, affected)
    return GroundingResult(
        parsed_files=len(parsed.files),
        truncated=parsed.truncated,
        changed=changed,
        base_compat=compat,
        affected=affected,
        mermaid=mermaid,
        summary={
            **summarize(parsed),
            "changed_symbols": [c.name for c in changed],
            "affected_symbols": sorted({a["target_symbol"] for a in affected}),
            "base_compat": compat["status"],
        },
    )
