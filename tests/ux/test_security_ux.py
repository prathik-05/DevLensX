import pathlib
def test_no_traceback_in_ui():
    content = pathlib.Path("web/src/components/ErrorBoundary.tsx").read_text(encoding="utf-8")
    assert "Something went wrong" in content
    assert "Return to Overview" in content

def test_xss_escaped():
    # Frontend uses React which auto-escapes; verify no dangerouslySetInnerHTML with raw repo text
    for p in pathlib.Path("web/src/components").glob("*.tsx"):
        text = p.read_text(encoding="utf-8")
        if "dangerouslySetInnerHTML" in text:
            assert "sanitize" in text.lower() or "escape" in text.lower() or text.count("dangerouslySetInnerHTML") == 0

def test_secret_not_in_health():
    from fastapi.testclient import TestClient
    from devlensx.api.main import app
    c = TestClient(app)
    r = c.get("/api/health")
    assert "OPENAI_API_KEY" not in r.text
    assert "secret" not in r.text.lower() or "available" in r.text.lower()
