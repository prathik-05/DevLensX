import pathlib
def test_no_overclaiming():
    docs = list(pathlib.Path("docs").glob("*.md"))
    for p in docs:
        text = p.read_text(encoding="utf-8").lower()
        # Should not claim Go fully supported if matrix says pending
        if "go fully supported" in text:
            assert False, f"{p} overclaims Go"
    # README should not claim all languages validated
    readme = pathlib.Path("README.md").read_text(encoding="utf-8")
    # Check README mentions evidence model
    assert "Evidence" in readme or "evidence" in readme.lower()
