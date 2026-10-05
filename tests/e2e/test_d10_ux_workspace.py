import pathlib
def test_d10_workspace():
    content = pathlib.Path("web/src/workspaceContext.tsx").read_text(encoding="utf-8")
    assert "active_symbol" in content
    assert "active_page" in content
    assert "analysis_run_id" in content
    # DocsPage preserves context
    assert "setContext" in pathlib.Path("web/src/components/DocsPage.tsx").read_text(encoding="utf-8")
