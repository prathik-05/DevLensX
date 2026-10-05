import sys
sys.path.insert(0, '.')
from devlensx.chat.orchestrator import ChatOrchestrator
from devlensx.evidence.models import SnapshotRecord
from devlensx.evidence.resolver import get_snapshot_registry

def test_chat_streaming():
    # Need a snapshot
    from devlensx.chat.orchestrator import store_model
    snap = get_snapshot_registry().register("test-stream", "run-stream", ".", None)
    store_model("run-stream", {"classes": [{"name": "OwnerController", "file": "OwnerController.java", "line_start": 1, "line_end": 10, "stereotype": "Controller", "kind": "class"}], "relationships": []})
    events = list(ChatOrchestrator.stream("run-stream", "Where is authentication?", mode="DEEP_RESEARCH"))
    ev_names = [e.split("event:")[1].split("\n")[0].strip() if "event:" in e else "" for e in events]
    assert any("research_started" in e for e in events)
    assert any("answer_token" in e for e in events)
    assert any("research_complete" in e for e in events)
    print("streaming ok", ev_names[:3])