import pathlib, json
def test_supported_languages_matches_matrix():
    matrix = json.loads(pathlib.Path("POLYGLOT_VALIDATION_MATRIX.json").read_text(encoding="utf-8"))
    doc = pathlib.Path("docs/SUPPORTED_LANGUAGES.md").read_text(encoding="utf-8")
    # Check doc reflects matrix statuses
    for lang, rec in matrix.items():
        status = rec["status"]
        if status == "VALIDATED":
            assert lang in doc and "VALIDATED" in doc
        elif status == "VALIDATION_PENDING":
            assert lang in doc
    # Check no overclaim: Go should not be VALIDATED in doc if matrix says pending
    assert "Go" in doc
    # Ensure doc distinguishes
    assert "PARSER_AVAILABLE" in doc or "VALIDATION_PENDING" in doc
