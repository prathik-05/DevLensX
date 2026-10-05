import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from devlensx.api.main import app
client = TestClient(app)

def test_chat_petclinic():
    r = client.post('/api/analyze', json={'repo_path': 'eval_repos/spring-petclinic'})
    run = r.json()['analysis_run_id']
    resp = client.post(f'/api/chat/{run}', json={'message': 'Which repository does OwnerController depend on?', 'mode': 'FAST'})
    assert resp.status_code == 200
    j = resp.json()
    assert any(c['subject']=='OwnerController' and 'OwnerRepository' in c['object'] and 'VERIFIED' in c['verdict'] for c in j['claims'])
    assert len(j['evidence_refs']) > 0
    print("petclinic chat ok")