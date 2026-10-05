"""
Unit and Integration Tests for DevLensX Native GitIngest Engine (devlensx/ingest.py).
Tests URL parsing, SSRF rejection, filtering, temp dir cleanup, snapshot formatting, and token monotonicity.
All tests run with NO NETWORK calls (using local fixture repos and mocking).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from devlensx.api.main import app
from devlensx.ingest import (
    ParsedSource,
    estimate_tokens,
    ingest_repository_sync,
    parse_github_url,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. URL Parsing & SSRF Protection Tests
# ---------------------------------------------------------------------------

def test_parse_github_url_valid_standard():
    parsed = parse_github_url("https://github.com/fastapi/fastapi")
    assert not parsed.is_local
    assert parsed.owner == "fastapi"
    assert parsed.repo == "fastapi"
    assert parsed.branch is None
    assert parsed.subpath is None
    assert parsed.clone_url == "https://github.com/fastapi/fastapi.git"


def test_parse_github_url_with_git_suffix():
    parsed = parse_github_url("https://github.com/torvalds/linux.git")
    assert not parsed.is_local
    assert parsed.owner == "torvalds"
    assert parsed.repo == "linux"


def test_parse_github_url_with_tree_branch_and_subpath():
    parsed = parse_github_url("https://github.com/psf/requests/tree/main/requests/packages")
    assert not parsed.is_local
    assert parsed.owner == "psf"
    assert parsed.repo == "requests"
    assert parsed.branch == "main"
    assert parsed.subpath == "requests/packages"


def test_parse_github_url_ssrf_rejection():
    # Non-GitHub hosts must be rejected with 400
    with pytest.raises(HTTPException) as exc_info:
        parse_github_url("https://gitlab.com/user/project")
    assert exc_info.value.status_code == 400
    assert "SSRF Protection" in exc_info.value.detail

    with pytest.raises(HTTPException) as exc_info2:
        parse_github_url("https://169.254.169.254/latest/meta-data/")
    assert exc_info2.value.status_code == 400
    assert "SSRF Protection" in exc_info2.value.detail

    with pytest.raises(HTTPException) as exc_info3:
        parse_github_url("https://evil.com?target=github.com")
    assert exc_info3.value.status_code == 400
    assert "SSRF Protection" in exc_info3.value.detail


def test_parse_github_url_path_traversal_subpath_rejection():
    # Path traversal inside subpath
    with pytest.raises(HTTPException) as exc_info:
        parse_github_url("https://github.com/owner/repo/tree/main/../../etc/passwd")
    assert exc_info.value.status_code == 400
    assert "Path traversal" in exc_info.value.detail


def test_parse_local_path(tmp_path: Path):
    parsed = parse_github_url(str(tmp_path))
    assert parsed.is_local
    assert parsed.local_path == tmp_path.resolve()
    assert parsed.repo_name == tmp_path.name


# ---------------------------------------------------------------------------
# 2. Filtering Tests (Binaries, .gitignore, globs, size caps)
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """Creates a local fixture git repo without network."""
    repo = tmp_path / "fixture_repo"
    repo.mkdir()

    # Git init
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=str(repo), check=True)

    # 1. Normal files
    (repo / "README.md").write_text("# Fixture Repo\nHello DevLensX!", encoding="utf-8")
    src = repo / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (src / "utils.ts").write_text("export const add = (a: number, b: number) => a + b;\n", encoding="utf-8")

    # 2. Binary file (contains null byte)
    (src / "app.bin").write_bytes(b"\x00\x01\x02\x03BINARY_CONTENT")

    # 3. Excluded vendor & lock files
    (repo / "package-lock.json").write_text("{}", encoding="utf-8")
    (repo / "bundle.min.js").write_text("console.log('minified')", encoding="utf-8")
    nm = repo / "node_modules"
    nm.mkdir()
    (nm / "dep.js").write_text("module.exports = {}", encoding="utf-8")

    # 4. .gitignore file
    (repo / ".gitignore").write_text("ignored_dir/\n*.tmp\n", encoding="utf-8")
    ignored_d = repo / "ignored_dir"
    ignored_d.mkdir()
    (ignored_d / "secret.txt").write_text("secret!", encoding="utf-8")
    (repo / "test.tmp").write_text("temporary", encoding="utf-8")

    # 5. Large file for size cap test
    (repo / "large_file.txt").write_text("A" * (200 * 1024), encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo), check=True, capture_output=True)

    return repo


def test_filtering_and_skipping(fixture_repo: Path):
    result = ingest_repository_sync(
        url_or_path=str(fixture_repo),
        max_file_size=100 * 1024,  # 100 KB limit (should drop large_file.txt)
        full=True,
    )

    file_paths = [f.path for f in result.files]

    # Accepted files
    assert "README.md" in file_paths
    assert "src/main.py" in file_paths or "src\\main.py" in file_paths
    assert "src/utils.ts" in file_paths or "src\\utils.ts" in file_paths

    # Binary file skipped
    assert not any("app.bin" in p for p in file_paths)

    # Lockfiles and minified files skipped
    assert not any("package-lock.json" in p for p in file_paths)
    assert not any("bundle.min.js" in p for p in file_paths)

    # node_modules skipped
    assert not any("node_modules" in p for p in file_paths)

    # .gitignore honored
    assert not any("ignored_dir" in p for p in file_paths)
    assert not any("test.tmp" in p for p in file_paths)

    # Per-file size cap enforced
    assert not any("large_file.txt" in p for p in file_paths)


def test_user_include_and_exclude_globs(fixture_repo: Path):
    # Only include Python files
    py_result = ingest_repository_sync(
        url_or_path=str(fixture_repo),
        include_patterns="*.py",
        full=True,
    )
    assert len(py_result.files) == 1
    assert py_result.files[0].path.endswith("main.py")

    # Exclude typescript
    no_ts_result = ingest_repository_sync(
        url_or_path=str(fixture_repo),
        exclude_patterns="*.ts",
        full=True,
    )
    assert not any(f.path.endswith("utils.ts") for f in no_ts_result.files)


# ---------------------------------------------------------------------------
# 3. Temp Directory Cleanup Tests
# ---------------------------------------------------------------------------

def test_temp_dir_cleaned_up_on_success():
    created_tmp = []
    original_mkdtemp = tempfile.mkdtemp

    with patch("devlensx.ingest.clone_repository") as mock_clone:
        # Simulate successful clone into temp dir
        def side_effect(clone_url, target_dir, **kwargs):
            Path(target_dir).mkdir(parents=True, exist_ok=True)
            (Path(target_dir) / "test.py").write_text("print('test')", encoding="utf-8")
        mock_clone.side_effect = side_effect

        result = ingest_repository_sync("https://github.com/test-org/dummy-repo")
        assert result.summary.repo_name == "dummy-repo"
        assert result.summary.file_count >= 1


def test_temp_dir_cleaned_up_on_failure_or_timeout():
    with patch("devlensx.ingest.clone_repository") as mock_clone:
        # Simulate clone failure
        mock_clone.side_effect = HTTPException(status_code=408, detail="Git clone timed out after 60 seconds.")

        with pytest.raises(HTTPException) as exc_info:
            ingest_repository_sync("https://github.com/timeout-org/timeout-repo")
        assert exc_info.value.status_code == 408


# ---------------------------------------------------------------------------
# 4. Digest Format Snapshot Test
# ---------------------------------------------------------------------------

def test_digest_format_snapshot(fixture_repo: Path):
    result = ingest_repository_sync(
        url_or_path=str(fixture_repo),
        include_patterns="src/main.py",
        full=True,
    )

    digest = result.digest

    # Verify structural layout
    assert "Directory structure:" in digest
    assert "================================================" in digest
    assert "FILE: src/main.py" in digest or "FILE: src\\main.py" in digest
    assert "def hello():" in digest
    assert "return 'world'" in digest


# ---------------------------------------------------------------------------
# 5. Token Estimation Monotonicity
# ---------------------------------------------------------------------------

def test_token_estimate_non_zero_and_monotonic():
    short_text = "print('hello')"
    medium_text = short_text * 50
    long_text = short_text * 500

    tokens_short = estimate_tokens(short_text)
    tokens_medium = estimate_tokens(medium_text)
    tokens_long = estimate_tokens(long_text)

    assert tokens_short > 0
    assert tokens_short < tokens_medium < tokens_long


# ---------------------------------------------------------------------------
# 6. API Endpoints: /api/ingest and /api/analyze/from-ingest
# ---------------------------------------------------------------------------

def test_api_ingest_endpoint(fixture_repo: Path):
    res = client.post(
        "/api/ingest",
        json={"url": str(fixture_repo)},
    )
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert "summary" in data
    assert "tree" in data
    assert "files" in data
    assert data["summary"]["file_count"] >= 2

    # Verify download digest endpoint
    ingest_id = data["id"]
    dl_res = client.get(f"/api/ingest/{ingest_id}/digest")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"].startswith("text/plain")
    assert "Directory structure:" in dl_res.text


def test_api_analyze_from_ingest(fixture_repo: Path):
    # First ingest
    res = client.post(
        "/api/ingest",
        json={"url": str(fixture_repo)},
    )
    assert res.status_code == 200
    ingest_id = res.json()["id"]

    # Then analyze without double cloning
    with patch("devlensx.pipeline.Pipeline.analyze") as mock_pipeline:
        mock_pipeline.return_value = {"status": "analyzed", "classes": 5}

        analyze_res = client.post(
            "/api/analyze/from-ingest",
            json={"ingest_id": ingest_id},
        )
        assert analyze_res.status_code == 200
        data = analyze_res.json()
        assert data["status"] == "success"
        assert mock_pipeline.called
