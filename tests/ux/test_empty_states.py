import pathlib
def test_empty_state_components_exist():
    assert pathlib.Path("web/src/components/EmptyState.tsx").exists()
    assert pathlib.Path("web/src/components/ErrorBoundary.tsx").exists()
    assert pathlib.Path("web/src/components/StatusIndicator.tsx").exists()
    content = pathlib.Path("web/src/components/EmptyState.tsx").read_text(encoding="utf-8")
    assert "No documentation generated yet" in content or "EmptyState" in content
    assert "StaleState" in content
    assert "LoadingState" in content
