import json, time
from pathlib import Path
from typing import Dict, Any, List

BASELINE_PATH = Path("perf_baseline.json")

def save_baseline(data: Dict[str, Any]):
    BASELINE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_baseline() -> Dict[str, Any]:
    if BASELINE_PATH.exists():
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {}

def compare_to_baseline(current: Dict[str, Any], threshold: float = 1.20) -> Dict[str, Any]:
    baseline = load_baseline()
    violations = []
    for repo, metrics in current.items():
        base = baseline.get(repo, {})
        if not base: continue
        cur_total = metrics.get("total", {}).get("wall_clock_ms", 0)
        base_total = base.get("total", {}).get("wall_clock_ms", 0)
        if base_total and cur_total > base_total * threshold:
            violations.append({"repo": repo, "current": cur_total, "baseline": base_total, "ratio": round(cur_total/base_total,2)})
    return {"violations": violations, "threshold": threshold}

def generate_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    report = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "repositories": {}}
    for r in results:
        repo = r.get("repo", "unknown")
        report["repositories"][repo] = r
    return report
