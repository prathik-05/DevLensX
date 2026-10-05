import sys
sys.path.insert(0, '.')
from devlensx.evidence.models import SnapshotRecord
from devlensx.chat.synthesis import synthesize_answer
from devlensx.chat.models import ChatEvidence

def test_chat_claim_verification():
    snap = SnapshotRecord(repository_id="test", analysis_run_id="run1", repo_path=".", commit_hash=None)
    classes = [
        {"name": "OwnerController", "file": "OwnerController.java", "line_start": 10, "line_end": 30, "id": "java_OwnerController_1"},
        {"name": "OwnerRepository", "file": "OwnerRepository.java", "line_start": 5, "line_end": 20, "id": "java_OwnerRepository_2"},
    ]
    rels = [{"source": "java_OwnerController_1", "target": "OwnerRepository", "type": "DEPENDS_ON"}]
    ev = ChatEvidence(deterministic_symbols=classes, deterministic_relationships=rels, deterministic_source_refs=[])
    answer, claims, refs = synthesize_answer("Which repository does OwnerController depend on?", ev, mode="FAST", snapshot=snap, classes=classes, relationships=rels)
    # Should have a VERIFIED claim for OwnerController -> OwnerRepository
    found = [c for c in claims if c['subject']=='OwnerController' and 'OwnerRepository' in c['object'] and 'VERIFIED' in c['verdict']]
    assert found, claims
    # Fake tech should be INSUFFICIENT when queried
    ev2 = ChatEvidence(deterministic_symbols=classes, deterministic_relationships=[], deterministic_source_refs=[])
    answer2, claims2, refs2 = synthesize_answer("How does Redis handle caching?", ev2, mode="FAST", snapshot=snap, classes=classes, relationships=[])
    redis_claims = [c for c in claims2 if 'redis' in c['subject'].lower() or 'redis' in c['object'].lower()]
    assert any('INSUFFICIENT' in c['verdict'] for c in redis_claims), claims2
    print("claim verification ok")