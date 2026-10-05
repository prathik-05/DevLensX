import sys
sys.path.insert(0, '.')
from devlensx.evidence.models import SnapshotRecord
from devlensx.chat.fast_mode import run_fast

def test_fast_mode():
    snap = SnapshotRecord(repository_id="test", analysis_run_id="run1", repo_path=".", commit_hash=None)
    model = {
        "classes": [
            {"name": "OwnerController", "file": "OwnerController.java", "line_start": 10, "line_end": 30, "stereotype": "Controller", "kind": "class", "methods": []},
            {"name": "OwnerRepository", "file": "OwnerRepository.java", "line_start": 5, "line_end": 20, "stereotype": "Repository", "kind": "interface", "methods": []},
        ],
        "relationships": [{"source": "OwnerController", "target": "OwnerRepository", "type": "DEPENDS_ON"}],
        "endpoints": [],
    }
    ans = run_fast(snap, model, "Where is authentication?", context=None)
    assert ans.mode.value == "FAST"
    # Should have small evidence set
    assert len(ans.evidence_refs) <= 8
    print("fast ok", ans.answer[:80])