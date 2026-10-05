import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from devlensx.api.main import app
client = TestClient(app)

def test_chat_repository_isolation():
    r1 = client.post('/api/analyze', json={'repo_path': 'eval_repos/spring-petclinic'})
    run1 = r1.json()['analysis_run_id']
    r2 = client.post('/api/analyze', json={'repo_path': 'eval_repos/battleship-python'})
    run2 = r2.json()['analysis_run_id']
    # Ask petclinic question on petclinic run -> should be VERIFIED
    j1 = client.post(f'/api/chat/{run1}', json={'message': 'Which repository does OwnerController depend on?', 'mode': 'FAST'}).json()
    assert any(c['subject']=='OwnerController' for c in j1['claims'])
    # Same question on battleship run must NOT yield VERIFIED OwnerController claim
    j2 = client.post(f'/api/chat/{run2}', json={'message': 'Which repository does OwnerController depend on?', 'mode': 'FAST'}).json()
    verified_owner = [c for c in j2['claims'] if c['subject']=='OwnerController' and 'VERIFIED' in c['verdict']]
    assert not verified_owner, f"Cross-repo leak: {verified_owner}"
    # Back to petclinic must still work
    j3 = client.post(f'/api/chat/{run1}', json={'message': 'Which repository does OwnerController depend on?', 'mode': 'FAST'}).json()
    assert any(c['subject']=='OwnerController' and 'VERIFIED' in c['verdict'] for c in j3['claims'])
    print("isolation ok")