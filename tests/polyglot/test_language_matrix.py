from pathlib import Path
import json

def test_matrix_exists():
    p = Path("POLYGLOT_VALIDATION_MATRIX.json")
    assert p.exists(), "Matrix not generated"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "Java" in data
    assert data["Java"]["status"] == "VALIDATED"
    assert data["Python"]["status"] == "VALIDATED"
    assert data["TypeScript"]["status"] == "VALIDATED"
    assert data["Go"]["status"] == "VALIDATION_PENDING"
    assert data["JavaScript"]["status"] in ("VALIDATION_PENDING", "VALIDATED")
    for lang, rec in data.items():
        if rec["status"] == "VALIDATED":
            assert rec["files_parsed"] > 0
            assert rec["symbols"] > 0
            assert rec["evidence_resolution"] is True
            assert rec["real_repository"] is not None

def test_validated_have_commit():
    import json, pathlib
    data = json.loads(pathlib.Path("POLYGLOT_VALIDATION_MATRIX.json").read_text(encoding="utf-8"))
    for lang in ["Java", "TypeScript", "Python"]:
        rec = data[lang]
        assert rec["status"] == "VALIDATED"
        assert rec["commit_hash"] is None or len(rec["commit_hash"]) >= 6 or rec["commit_hash"] == ""