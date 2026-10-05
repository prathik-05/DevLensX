import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from devlensx.api.main import app
client = TestClient(app)

def test_chat_adversarial():
    r = client.post('/api/analyze', json={'repo_path': 'eval_repos/spring-petclinic'})
    run = r.json()['analysis_run_id']
    for tech in ["Redis", "Kafka", "PaymentService"]:
        resp = client.post(f'/api/chat/{run}', json={'message': f'How does {tech} handle caching?', 'mode': 'FAST'})
        j = resp.json()
        # Any claim mentioning the fake tech must not be VERIFIED
        bad = [c for c in j['claims'] if tech.lower() in c['subject'].lower() or tech.lower() in c['object'].lower()]
        for c in bad:
            assert 'VERIFIED' not in c['verdict'], f"Hallucinated {tech} was VERIFIED: {c}"
            assert 'INSUFFICIENT' in c['verdict'] or 'SUGGESTION' in c['verdict']
        # No fake citation for the tech
        assert not any(tech.lower() in str(ref).lower() and 'VERIFIED' in str(c.get('verdict','')) for ref in j['evidence_refs'] for c in j['claims'] if tech.lower() in c['object'].lower())
    print("adversarial ok")