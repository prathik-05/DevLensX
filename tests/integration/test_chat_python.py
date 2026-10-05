import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from devlensx.api.main import app
client = TestClient(app)

def test_chat_python():
    r = client.post('/api/analyze', json={'repo_path': 'eval_repos/battleship-python'})
    run = r.json()['analysis_run_id']
    resp = client.post(f'/api/chat/{run}', json={'message': 'Explain this repository', 'mode': 'FAST'})
    assert resp.status_code == 200
    j = resp.json()
    assert j['answer']
    print("python chat ok")