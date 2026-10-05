import pathlib
REQUIRED = ["README.md","docs/ARCHITECTURE.md","docs/INSTALLATION.md","docs/SECURITY.md","docs/SUPPORTED_LANGUAGES.md","docs/EVIDENCE_MODEL.md","docs/WIKI.md","docs/DIAGRAMS.md","docs/CHAT.md","docs/WORKSPACE.md","docs/INCREMENTAL_ANALYSIS.md","docs/PERFORMANCE.md","docs/EVALUATION.md","docs/OBSERVABILITY.md","docs/TESTING.md","docs/TROUBLESHOOTING.md","docs/RELEASE.md"]
def test_docs_exist():
    for p in REQUIRED:
        assert pathlib.Path(p).exists(), f"Missing {p}"
