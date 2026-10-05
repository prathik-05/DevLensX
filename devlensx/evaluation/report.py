import json, time, pathlib
from typing import List, Dict, Any

REPORT_PATH = pathlib.Path("GOLDEN_EVALUATION_REPORT.json")

def generate_report(cases, results):
    verified = sum(1 for r in results if r.get("expected_verdict")=="VERIFIED" and r.get("passed"))
    insufficient = sum(1 for r in results if r.get("expected_verdict")=="INSUFFICIENT_EVIDENCE" and r.get("passed"))
    suggestions = sum(1 for r in results if r.get("expected_verdict")=="AI_SUGGESTION" and r.get("passed"))
    return {
        "dataset_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repositories": list({c.repository for c in cases}),
        "cases": len(cases),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "verified_claims": verified,
        "insufficient_claims": insufficient,
        "suggestions": suggestions,
        "evidence_resolution_failures": sum(1 for r in results if not r["passed"] and "evidence" in (r.get("error") or "").lower()),
        "snapshot_isolation_failures": sum(1 for r in results if not r["passed"] and "snapshot" in (r.get("error") or "").lower()),
        "details": results
    }

def save_report(report):
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return REPORT_PATH
