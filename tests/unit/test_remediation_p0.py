"""
DevLensX Unit Test: P0 Remediation Verification
Tests:
1. /api/explorer/file-content returns real file content for active snapshot.
2. /api/explorer/file-content rejects path traversal.
3. /api/upload-zip rejects ZIP archives containing symlinks.
4. Grounded reasoning returns honest INSUFFICIENT_EVIDENCE when evidence is absent.
"""

import io
import stat
import zipfile
import pytest
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence import get_snapshot_registry
from devlensx.reasoning.engine import RepositoryReasoningEngine


def test_explorer_file_content_and_traversal_protection():
    client = TestClient(app)
    
    # 1. Valid file content
    resp = client.get("/api/explorer/file-content?file_path=devlensx/core/config.py")
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_path"] == "devlensx/core/config.py"
    assert not data["is_binary"]
    assert len(data["lines"]) > 0
    assert "JWT_SECRET" in data["content"]

    # 2. Path traversal attempt must be rejected with 404/400 (not escaped)
    resp_traversal = client.get("/api/explorer/file-content?file_path=../../Windows/System32/drivers/etc/hosts")
    assert resp_traversal.status_code in (404, 400)


def test_zip_symlink_rejection():
    client = TestClient(app)
    
    # Create an in-memory zip archive containing a symlink
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Create normal file
        zf.writestr("test.py", "print('hello')")
        # Create a symlink entry
        symlink_info = zipfile.ZipInfo("evil_link")
        symlink_info.create_system = 3  # Unix
        symlink_info.external_attr = stat.S_IFLNK << 16  # mark as symlink
        zf.writestr(symlink_info, "/etc/passwd")
    
    buf.seek(0)
    files = {"file": ("repo_with_symlink.zip", buf.getvalue(), "application/zip")}
    resp = client.post("/api/upload-zip", files=files)
    assert resp.status_code == 403
    assert "Symlinks are prohibited" in resp.json()["detail"]


def test_grounded_reasoning_insufficient_evidence():
    engine = RepositoryReasoningEngine(llm_provider=None)
    # Question on empty model must return honest INSUFFICIENT_EVIDENCE
    res = engine.answer_repository_question(
        question="what is this repository about",
        repo_model={"classes": [], "repository": "EmptyRepo"}
    )
    assert res["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert "INSUFFICIENT_EVIDENCE" in res["answer"]
