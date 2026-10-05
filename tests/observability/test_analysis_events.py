from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.observability.events import get_events, clear_events
def test_analysis_events():
    clear_events()
    c = TestClient(app)
    r = c.post("/api/analyze", json={"repo_path": "eval_repos/battleship-python"})
    assert r.status_code == 200
    evs = get_events()
    assert any(e["event"]=="analysis_started" for e in evs)
    # analysis_completed should have analysis_run_id
    assert r.json().get("analysis_run_id")
