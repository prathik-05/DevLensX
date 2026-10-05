def test_d10_loading_states():
    # Verify LoadingState component exists and has expected text
    p = __import__("pathlib").Path("web/src/components/EmptyState.tsx")
    assert "Analyzing repository" in p.read_text(encoding="utf-8")
    assert "LoadingState" in p.read_text(encoding="utf-8")
