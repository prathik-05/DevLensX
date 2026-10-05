import json, pathlib
def test_d10_unsupported():
    m = json.loads(pathlib.Path("POLYGLOT_VALIDATION_MATRIX.json").read_text(encoding="utf-8"))
    # At least 3 validated, others pending
    validated = [k for k,v in m.items() if v["status"]=="VALIDATED"]
    pending = [k for k,v in m.items() if v["status"]=="VALIDATION_PENDING"]
    assert len(validated) >= 3
    assert len(pending) >= 2
    # UI should distinguish
    content = pathlib.Path("devlensx/polyglot/models.py").read_text(encoding="utf-8")
    assert "VALIDATION_PENDING" in content
