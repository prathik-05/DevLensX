"""
DevLensX Evaluation Lab API Routes (D10 / Golden Benchmark)

Exposes endpoints for running and inspecting the Golden Evaluation Suite.
All metrics are strictly dynamic and computed from real evaluation results.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
from pathlib import Path

from devlensx.evaluation.runner import GoldenRunner
from devlensx.evaluation.dataset import load_dataset
from devlensx.evaluation.report import generate_report, REPORT_PATH

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


class EvaluationRunRequest(BaseModel):
    limit: Optional[int] = None
    repository: Optional[str] = None
    mode: Optional[str] = None


@router.post("/run")
def run_evaluation(req: Optional[EvaluationRunRequest] = None):
    """
    Run evaluation on the Golden Dataset or a specified subset.
    Returns real, dynamically computed evaluation metrics and verified evidence cases.
    """
    try:
        cases = GoldenRunner.ensure_dataset()
        if req:
            if req.repository:
                cases = [c for c in cases if c.repository == req.repository]
            if req.limit and req.limit > 0:
                cases = cases[:req.limit]

        report = GoldenRunner.run_all(cases)

        # Build cases array for frontend EvaluationView
        cases_list = []
        for d in report.get("details", []):
            cid = d.get("id")
            orig = next((c for c in cases if c.id == cid), None)
            res = d.get("result", {})
            cases_list.append({
                "id": cid,
                "question": orig.question if orig else cid,
                "repository": orig.repository if orig else res.get("repository_id", ""),
                "expected_verdict": d.get("expected_verdict", "VERIFIED"),
                "passed": d.get("passed", False),
                "error": d.get("error"),
                "result": res,
            })

        # Provide cases as list for UI and case_count for tests/clarity
        report["case_count"] = len(cases_list)
        report["cases"] = cases_list
        report["results"] = cases_list
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation run failed: {e}")


@router.get("/report")
def get_evaluation_report():
    """Get the latest golden evaluation report."""
    if REPORT_PATH.exists():
        try:
            data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            return data
        except Exception:
            pass
    # If no report on disk yet, run a fast benchmark subset and return
    cases = GoldenRunner.ensure_dataset()
    report = GoldenRunner.run_all(cases[:5])
    return report


@router.get("/dataset")
def get_evaluation_dataset():
    """Get the golden evaluation cases dataset."""
    cases = GoldenRunner.ensure_dataset()
    return {"cases": [c.to_dict() for c in cases], "count": len(cases)}
