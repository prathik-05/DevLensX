"""Review engine — deterministic what changed / affected vs AI suggestion what might break."""

from typing import Dict, Any, List, Optional
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.review.diff_analyzer import DiffAnalyzer
from devlensx.review.grounding import (
    ground_diff, BASE_MISMATCH, EXACT_SNAPSHOT, UNKNOWN_BASE,
)
from devlensx.evidence.models import EvidenceRef, EvidenceType

class ReviewEngine:
    @staticmethod
    def review(diff: str, analysis_run_id: str, base_commit: Optional[str] = None) -> Dict[str, Any]:
        snap = get_snapshot_registry().get(analysis_run_id)
        if not snap:
            raise ValueError(f"UNKNOWN_RUN:{analysis_run_id}")
        # P1-C: per-run model only (ReviewEngine.review previously fell back
        # to process-global latest — same hole as review-repo pre-P1-A).
        model = {}
        try:
            from devlensx.chat.orchestrator import _model_store
            model = _model_store.get(analysis_run_id) or {}
        except Exception:
            pass
        if not isinstance(model, dict) or not model.get("classes"):
            raise ValueError(f"MODEL_EVICTED:{analysis_run_id}")
        snapshot = {
            "repository_id": snap.repository_id,
            "analysis_run_id": snap.analysis_run_id,
            "commit_hash": snap.commit_hash,
        }
        # P1-C: one grounding call — parse, resolve, compat, affected, diagram.
        try:
            from devlensx.api.main import global_state
            gs_store = global_state.get("graph_store")
        except Exception:
            gs_store = None
        grounding = ground_diff(diff, model, snapshot, base_commit, gs_store)
        compat = grounding.base_compat
        use_changed_lines = compat["status"] != BASE_MISMATCH

        changed = DiffAnalyzer.changed_symbols(diff, model)
        # Affected set: deterministic grounding (Kuzu hop-1 intersected with
        # snapshot model + model-edge BFS). Never from the LLM.
        affected = [
            {"symbol": a["target_symbol"], "file": a.get("file", ""),
             "relationship": a.get("relationship", ""), "via": a.get("via", ""),
             "hop": a.get("hop", 1), "status": "VERIFIED"}
            for a in grounding.affected
        ]
        # Related tests among changed + affected
        tests = [
            c for c in changed if c.get("is_test") or "Test" in c.get("name","")
        ] + [
            {"name": a["target_symbol"], "file": a.get("file",""), "is_test": True}
            for a in grounding.affected if a.get("relationship") == "TESTS"
        ]
        # Build evidence refs for changed symbols. On BASE_MISMATCH the
        # changed-line ranges are downgraded to declaration spans so refs
        # never point at wrong code with valid-looking lines.
        refs = []
        for c in changed:
            dc = c.get("diff_change") or {}
            lines = dc.get("changed_lines") or []
            rlines = dc.get("removed_lines") or []
            if use_changed_lines and lines:
                ls, le = min(lines), max(lines)
            elif use_changed_lines and rlines:
                ls, le = min(rlines), max(rlines)
            else:
                ls, le = int(c.get("line_start") or 1), int(c.get("line_end") or 1)
            refs.append(EvidenceRef(
                repository_id=snap.repository_id,
                analysis_run_id=snap.analysis_run_id,
                commit_hash=snap.commit_hash,
                file_path=(c.get("file") or "").replace("\\","/"),
                line_start=ls,
                line_end=le,
                symbol_name=c.get("name"),
                evidence_type=EvidenceType.AST,
            ).to_dict())
        # Snapshot-bound refs for affected entities (provenance, not verdicts)
        affected_refs = []
        for a in grounding.affected:
            for r in a.get("evidence_refs", [])[:1]:
                affected_refs.append(r)
        return {
            "repository_id": snap.repository_id,
            "analysis_run_id": snap.analysis_run_id,
            "commit_hash": snap.commit_hash,
            "base_compat": compat,
            "what_changed": [
                {
                    "symbol": c["name"],
                    "file": c.get("file",""),
                    "status": "VERIFIED",
                    "change": (c.get("diff_change") or {}).get("change", "MODIFIED"),
                    "changed_lines": (c.get("diff_change") or {}).get("changed_lines", []),
                    "removed_lines": (c.get("diff_change") or {}).get("removed_lines", []),
                    "evidence_kind": (
                        (c.get("diff_change") or {}).get("evidence_kind", "declaration")
                        if use_changed_lines else "declaration"
                    ),
                }
                for c in changed
            ],
            "what_affected": affected,
            "related_tests": [{"symbol": t["name"], "status": "VERIFIED"} for t in tests],
            "what_might_break": [{"text": f"Change to {c['name']} may affect downstream {len(affected)} component(s)", "status": "AI_SUGGESTION"} for c in changed[:2]],
            "suspicious_patterns": [],
            "evidence_refs": refs,
            "affected_refs": affected_refs,
            "diagram": {
                "type": "CHANGE_FLOW",
                "mermaid": grounding.mermaid,
                "status": "VERIFIED",
            },
        }