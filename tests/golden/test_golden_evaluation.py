import json, pathlib
from devlensx.evaluation.runner import GoldenRunner

def test_golden_dataset_exists():
    assert pathlib.Path("GOLDEN_EVALUATION_DATASET.json").exists()
    data = json.loads(pathlib.Path("GOLDEN_EVALUATION_DATASET.json").read_text(encoding="utf-8"))
    assert data["dataset_version"] == "1.0"
    assert len(data["cases"]) >= 30

def test_golden_report_exists():
    # Runner should have generated report with all cases passing
    from pathlib import Path
    rep_path = Path("GOLDEN_EVALUATION_REPORT.json")
    assert rep_path.exists()
    data = json.loads(rep_path.read_text(encoding="utf-8"))
    assert data.get("cases", 0) >= 30
    assert data.get("passed", 0) >= 30
    assert data.get("failed", 1) == 0

def test_golden_adversarial():
    from devlensx.evaluation.dataset import load_dataset
    cases = load_dataset()
    adv = [c for c in cases if "negative" in c.id or "redis" in c.id.lower()]
    assert len(adv) >= 6
    for c in adv:
        assert c.expected_verdict.value == "INSUFFICIENT_EVIDENCE"
