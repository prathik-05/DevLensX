"""DevLensX Change Impact Analyzer — snapshot-bound AST & Graph blast radius."""

from typing import Dict, Any, List, Optional, Set
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.evidence.models import EvidenceRef, EvidenceType, SnapshotRecord
from devlensx.impact.models import ImpactResult


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
    def analyze(target_symbol: str, analysis_run_id: str) -> ImpactResult:
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

        # 3. Locate target symbol within this snapshot's classes
        target = next(
            (c for c in classes if c.get("name") == target_symbol or
             c.get("qualified_name") == target_symbol or
             c.get("name") == target_symbol.split(".")[-1]),
            None
        )
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

        # 4. Direct finding
        direct = [{
            "symbol": target_name,
            "file": (target.get("file") or "").replace("\\", "/"),
            "status": "VERIFIED",
            "evidence_ref": _ref_for_class(snap, target),
        }]

        # 5. Grounded Downstream (blast radius) via AST relationships & dependencies
        relationships = model.get("relationships", []) if isinstance(model, dict) else []
        extra_edges: Dict[str, Set[str]] = {}
        for r in relationships:
            if isinstance(r, dict):
                src = r.get("source")
                tgt = r.get("target")
                rtype = str(r.get("type", "")).upper()
                if src and tgt and rtype in ("DEPENDS_ON", "CALLS", "USES", "INJECTS", "REFERENCES", "EXTENDS", "IMPLEMENTS"):
                    extra_edges.setdefault(src, set()).add(tgt)
                    extra_edges.setdefault(src, set()).add(tgt.split(".")[-1])

        downstream_classes: List[Dict[str, Any]] = []
        visited: Set[str] = {target_name, target_symbol}
        queue: List[str] = [target_name]

        while queue and len(visited) <= _MAX_IAT + 1:
            curr = queue.pop(0)
            for c in classes:
                cname = c.get("name")
                if not cname or cname in visited:
                    continue
                cdeps = _get_class_dependencies(c)
                if cname in extra_edges:
                    cdeps.update(extra_edges[cname])

                # If class depends on curr, it is in curr's downstream blast radius
                if curr in cdeps or any(curr == dep.split(".")[-1] for dep in cdeps):
                    visited.add(cname)
                    downstream_classes.append(c)
                    queue.append(cname)

        downstream = [
            {
                "symbol": c["name"],
                "file": (c.get("file") or "").replace("\\", "/"),
                "status": "VERIFIED",
            }
            for c in downstream_classes
        ]

        # 6. Associated Tests
        tests: List[Dict[str, Any]] = []
        affected_names = {target_name, target_symbol} | {c["name"] for c in downstream_classes}
        for c in classes:
            cname = c.get("name", "")
            is_test = bool(
                c.get("is_test") or
                "Test" in cname or
                "test" in (c.get("file") or "").lower() or
                c.get("stereotype") == "Test"
            )
            if not is_test:
                continue

            cdeps = _get_class_dependencies(c)
            if cname in extra_edges:
                cdeps.update(extra_edges[cname])

            if affected_names.intersection(cdeps) or any(t.lower() in cname.lower() for t in affected_names):
                tests.append({
                    "symbol": cname,
                    "file": (c.get("file") or "").replace("\\", "/"),
                    "status": "VERIFIED",
                })

        # 7. Configurations mentioning target
        configs: List[Any] = []
        for cfg in model.get("configurations", [])[:5]:
            if target_name.lower() in str(cfg).lower() or target_symbol.lower() in str(cfg).lower():
                configs.append(cfg)

        # 8. Evidence Refs (strict AST bounds)
        evidence_refs: List[Dict[str, Any]] = [_ref_for_class(snap, target)]
        for dc in downstream_classes[:10]:
            evidence_refs.append(_ref_for_class(snap, dc))
        for tc in [c for c in classes if any(c.get("name") == t["symbol"] for t in tests)][:5]:
            evidence_refs.append(_ref_for_class(snap, tc))

        # 9. Deterministic Mermaid Diagram
        mermaid_lines = ["graph TD"]
        mermaid_lines.append(f'  target["{target_name} (Target)"]')
        mermaid_lines.append("  style target fill:#2563eb,stroke:#60a5fa,stroke-width:2px,color:#fff")
        for dc in downstream_classes[:6]:
            sname = dc.get("name", "Component")
            mermaid_lines.append(f'  c_{abs(hash(sname)) % 10000}["{sname}"] --> target')
        for tc in tests[:4]:
            tname = tc["symbol"]
            mermaid_lines.append(f'  t_{abs(hash(tname)) % 10000}["{tname}"] -.-> target')
        mermaid_str = "\n".join(mermaid_lines)

        diagram = {
            "type": "CHANGE_IMPACT",
            "mermaid": mermaid_str,
            "format": "mermaid",
            "content": mermaid_str,
        }

        # 10. Dynamic Risk Level calculation
        downstream_count = len(downstream)
        tests_count = len(tests)
        if downstream_count >= 5 or tests_count >= 3:
            risk_level = "HIGH"
        elif downstream_count >= 2 or tests_count >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

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
        )
