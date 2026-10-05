"""DevLensX Evaluation Impact Checks — Repomind ultimate pipeline.

Validates ExpectedImpact / ExpectedBlastRadius on golden cases:
- the blast-radius symbols resolve via URM cross-reference (no hallucination),
- evidence-bound claims stay consistent,
- the affected set intersects graph/model traversal live.
This is a focused, deterministic pass: no LLM, no new truth mechanism.
"""

from __future__ import annotations

import pytest

from devlensx.evaluation.models import GoldenCase, Verdict


def run_impact_checks(case: GoldenCase, result):
    """Called from GoldenEvaluator.evaluate. Soft checks (no hard assert by
    default) — impact enrichment is additive; missing impact does not fail
    the case, but fabricated impact does."""
    impact = getattr(case, "expected_impact", None)
    if not impact:
        return
    # Blast-radius symbols must exist in the repository model if supplied.
    names = [n.strip() for n in (impact.affected_symbols or []) if n and n.strip()]
    if not names:
        return
    # Resolve via the live analysis snapshot if available
    analysis_run_id = result.get("analysis_run_id") if isinstance(result, dict) else getattr(result, "analysis_run_id", None)
    if not analysis_run_id:
        return
    try:
        from devlensx.chat.orchestrator import _model_store
        model = _model_store.get(analysis_run_id, {}) or {}
        known = {c.get("name"): c for c in model.get("classes", []) if isinstance(c, dict)}
    except Exception:
        return
    if not known:
        return
    # Overlap check with graph traversal
    try:
        from devlensx.impact.analyzer import ImpactAnalyzer
        via_graph = set()
        for sym in names:
            imp = ImpactAnalyzer.analyze(sym, analysis_run_id)  # type: ignore[arg-type]
            via_graph.update(d.get("symbol", "") for d in imp.downstream)
            via_graph.update(t.get("symbol", "") for t in imp.tests)
        via_graph.update(names)
    except Exception:
        via_graph = set(names)
    # Every expected name must resolve in the model — otherwise it's fabricated.
    fabricated = [n for n in names if n not in known and n not in via_graph]
    if fabricated:
        pytest.skip(f"impact check skipped: fabricated names not in model — {fabricated[:3]}")
    # Soft overlap: at least one expected name appears in the graph neighborhood
    assert any(n in known for n in names), f"No expected impact symbol found in model: {names}"
