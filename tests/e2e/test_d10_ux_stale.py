import pathlib
def test_d10_stale():
    assert "stale" in pathlib.Path("web/src/components/EmptyState.tsx").read_text(encoding="utf-8").lower()
    assert "Re-analyze" in pathlib.Path("web/src/components/EmptyState.tsx").read_text(encoding="utf-8")
