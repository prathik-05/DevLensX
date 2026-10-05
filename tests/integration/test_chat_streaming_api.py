import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from devlensx.api.main import app
client = TestClient(app)

def test_chat_streaming():
    r = client.post('/api/analyze', json={'repo_path': 'eval_repos/spring-petclinic'})
    run = r.json()['analysis_run_id']
    resp = client.post(f'/api/chat/{run}/stream', json={'message': 'Explain authentication', 'mode': 'DEEP_RESEARCH'})
    assert resp.status_code == 200
    assert 'text/event-stream' in resp.headers.get('content-type','')
    assert 'event: research_started' in resp.text
    assert 'event: answer_token' in resp.text
    assert 'event: research_complete' in resp.text
    print("streaming http ok")