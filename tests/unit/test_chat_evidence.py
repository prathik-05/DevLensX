import sys
sys.path.insert(0, '.')
from devlensx.evidence.models import SnapshotRecord
from devlensx.chat.evidence_context import collect_evidence

def test_chat_evidence():
    snap = SnapshotRecord(repository_id="test", analysis_run_id="run1", repo_path=".", commit_hash=None)
    model = {
        "classes": [
            {"name": "OwnerController", "file": "OwnerController.java", "line_start": 10, "line_end": 30, "stereotype": "Controller", "kind": "class"},
            {"name": "OwnerRepository", "file": "OwnerRepository.java", "line_start": 5, "line_end": 20, "stereotype": "Repository", "kind": "interface"},
        ],
        "relationships": [{"source": "OwnerController", "target": "OwnerRepository", "type": "DEPENDS_ON"}],
        "endpoints": [],
        "configurations": [],
    }
    ev = collect_evidence(snap, model, "Where is authentication?", top_k=5)
    assert not ev.is_empty()
    assert len(ev.deterministic_symbols) > 0
    # Contextual boost: selected symbol must be present
    from devlensx.chat.models import ChatContext
    ctx = ChatContext(repository_id="test", analysis_run_id="run1", selected_symbol="OwnerController")
    ev2 = collect_evidence(snap, model, "Explain this", context=ctx)
    assert any(s["name"] == "OwnerController" for s in ev2.deterministic_symbols)
    print("evidence ok")