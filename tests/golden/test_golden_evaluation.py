import json, pathlib
from devlensx.evaluation.runner import GoldenRunner

def test_golden_dataset_exists():
    assert pathlib.Path("GOLDEN_EVALUATION_DATASET.json").exists()
    data = json.loads(pathlib.Path("GOLDEN_EVALUATION_DATASET.json").read_text(encoding="utf-8"))
    assert data["dataset_version"] == "1.0"
    assert len(data["cases"]) >= 30

def test_golden_report_exists():
    # Runner should have generated report
    from pathlib import Path
    import devlensx.evaluation.runner
    # Ensure dataset
    cases = GoldenRunner.ensure_dataset()
    report = GoldenRunner.run_all(cases[:5])  # quick subset for test speed
    assert report["cases"] == 5
    assert report["passed"] + report["failed"] == 5

def test_golden_adversarial():
    from devlensx.evaluation.dataset import load_dataset
    cases = load_dataset()
    adv = [c for c in cases if "negative" in c.id or "redis" in c.id.lower()]
    assert len(adv) >= 6
    for c in adv:
        assert c.expected_verdict.value == "INSUFFICIENT_EVIDENCE"
