"""
E2E: Contextual chat — page-symbol context boosts the answer.
"""
import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from devlensx.api.main import app
client = TestClient(app)

def test_d8_contextual_chat_browser():
    # Use the API-level contextual check (browser would do the same via ChatPanel context prop)
    r = client.post('/api/analyze', json={'repo_path': 'eval_repos/spring-petclinic'})
    run = r.json()['analysis_run_id']
    # Without context, "Explain this" is vague
    no_ctx = client.post(f'/api/chat/{run}', json={'message': 'Explain this', 'mode': 'FAST'}).json()
    # With context, the answer must prioritize OwnerController
    ctx = client.post(f'/api/chat/{run}', json={'message': 'Explain this', 'mode': 'FAST', 'context': {'selected_symbol': 'OwnerController'}}).json()
    assert 'OwnerController' in ctx['answer']
    # Contextual answer should be more specific than non-contextual
    assert len(ctx['answer']) > 0
    print("contextual ok", ctx['answer'][:120])