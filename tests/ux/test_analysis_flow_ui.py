"""Analysis-flow UI tests: real wiring, honest states, no silent fake data."""
import pathlib

SRC = pathlib.Path("web/src")
STORE = (SRC / "store.ts").read_text(encoding="utf-8")
SIDEBAR = (SRC / "components/Sidebar.tsx").read_text(encoding="utf-8")
HEADER = (SRC / "components/Header.tsx").read_text(encoding="utf-8")
MAIN = (SRC / "main.tsx").read_text(encoding="utf-8")
APP = (SRC / "App.tsx").read_text(encoding="utf-8")
OVERVIEW = (SRC / "components/OverviewView.tsx").read_text(encoding="utf-8")
LANDING = (SRC / "components/LandingPage.tsx").read_text(encoding="utf-8")
API = (SRC / "apiClient.ts").read_text(encoding="utf-8")


def test_store_has_real_analysis_thunks():
    assert "runAnalysis" in STORE
    assert "uploadAndAnalyze" in STORE
    assert "analysisData" in STORE
    assert "analysisError" in STORE
    assert "analyzeRepo" in STORE
    # dead callback indirection removed
    assert "onRunAnalysis" not in STORE
    assert "onUploadZip" not in STORE


def test_providers_mounted_and_synced():
    assert "WorkspaceProvider" in MAIN
    assert "WikiProvider" in MAIN
    assert "WorkspaceSync" in APP
    assert "setContext" in APP


def test_sidebar_calls_thunks_directly():
    assert "runAnalysis" in SIDEBAR
    assert "uploadAndAnalyze" in SIDEBAR
    assert "analysisError" in SIDEBAR
    assert "onRunAnalysis?." not in SIDEBAR


def test_header_command_uses_thunk():
    assert "runAnalysis(repoPath)" in HEADER


def test_overview_honest_states():
    assert "No analysis yet" in OVERVIEW
    assert "Analysis failed" in OVERVIEW
    assert "parsing AST" in OVERVIEW
    # no fabricated metric literals remain
    for fake in ["142", "72.4", "'Add circuit breaker", "'Spring Boot'", "'Java'"]:
        assert fake not in OVERVIEW, fake


def test_landing_hero_input_modes():
    assert "ANALYZE A REPOSITORY" in LANDING
    assert "GitHub URL" in LANDING
    assert "Local Path" in LANDING
    assert "Upload .zip" in LANDING
    assert "uploadAndAnalyze" in LANDING
    assert "navigate('/overview')" in LANDING


def test_api_client_never_fakes_datasets():
    analyze_fn = API.split("export async function analyzeRepo")[1].split("export async function uploadZipRepo")[0]
    assert "getStandaloneRepoDataset" not in analyze_fn
    assert "throw new Error" in analyze_fn
    upload_fn = API.split("export async function uploadZipRepo")[1].split("export function getStandaloneRepoDataset")[0]
    assert "getStandaloneRepoDataset" not in upload_fn
    assert "throw new Error" in upload_fn
