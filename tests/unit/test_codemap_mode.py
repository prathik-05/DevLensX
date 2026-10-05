import sys
sys.path.insert(0, '.')
from devlensx.evidence.models import SnapshotRecord
from devlensx.chat.codemap_mode import run_codemap

def test_codemap_mode():
    snap = SnapshotRecord(repository_id="test", analysis_run_id="run1", repo_path=".", commit_hash=None)
    model = {
        "classes": [
            {"name": "OwnerController", "file": "OwnerController.java", "line_start": 10, "line_end": 30, "stereotype": "Controller", "kind": "class"},
            {"name": "OwnerService", "file": "OwnerService.java", "line_start": 10, "line_end": 30, "stereotype": "Service", "kind": "class"},
            {"name": "OwnerRepository", "file": "OwnerRepository.java", "line_start": 5, "line_end": 20, "stereotype": "Repository", "kind": "interface"},
        ],
        "relationships": [
            {"source": "OwnerController", "target": "OwnerService", "type": "DEPENDS_ON"},
            {"source": "OwnerService", "target": "OwnerRepository", "type": "DEPENDS_ON"},
        ],
        "endpoints": [],
    }
    ans = run_codemap(snap, model, "Trace the owner request to persistence", context=None)
    assert ans.mode.value == "CODEMAP"
    assert len(ans.diagrams) == 1
    assert "->" in ans.answer
    print("codemap ok", ans.diagrams[0])