import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from devlensx.api.main import app
client = TestClient(app)

def test_chat_typescript():
    r = client.post('/api/analyze', json={'repo_path': 'eval_repos/sp-portfolio'})
    run = r.json()['analysis_run_id']
    resp = client.post(f'/api/chat/{run}', json={'message': 'How does the theme system work?', 'mode': 'CODEMAP'})
    assert resp.status_code == 200
    j = resp.json()
    assert j['mode'] == 'CODEMAP'
    assert len(j['diagrams']) == 1
    print("typescript chat ok")