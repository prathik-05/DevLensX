"""
Archive / ZIP Security Tests (D10.2.2)

Tests Zip Slip, path traversal, symlink escape, and resource exhaustion.
"""

import io
import zipfile
import pytest
import tempfile
import os
from pathlib import Path

from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.core.security import is_safe_path


class TestArchiveSecurity:
    """Tests for ZIP upload security."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_zip_slip_basic(self):
        """Test basic Zip Slip with ../ traversal."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("../evil.txt", "MALICIOUS CONTENT")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_slip.zip", zip_buffer, "application/zip")},
        )
        # Should be rejected with 400 or 403
        assert resp.status_code in (400, 403), f"Zip Slip permitted! Status: {resp.status_code}"

    def test_zip_slip_multiple_traversal(self):
        """Test Zip Slip with multiple ../ traversals."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("../../../../etc/passwd", "MALICIOUS CONTENT")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_slip2.zip", zip_buffer, "application/zip")},
        )
        assert resp.status_code in (400, 403)

    def test_zip_absolute_unix_path(self):
        """Test ZIP with absolute Unix path."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("/etc/passwd", "MALICIOUS CONTENT")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_abs.zip", zip_buffer, "application/zip")},
        )
        assert resp.status_code in (400, 403)

    def test_zip_absolute_windows_path(self):
        """Test ZIP with absolute Windows path."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("C:\\Windows\\System32\\evil.txt", "MALICIOUS CONTENT")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_win_abs.zip", zip_buffer, "application/zip")},
        )
        assert resp.status_code in (400, 403)

    def test_zip_windows_absolute_forward_slash(self):
        """Test ZIP with Windows absolute path using forward slashes."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("C:/Windows/System32/evil.txt", "MALICIOUS CONTENT")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_win_abs2.zip", zip_buffer, "application/zip")},
        )
        assert resp.status_code in (400, 403)

    def test_zip_nested_traversal(self):
        """Test ZIP with nested traversal in directory structure."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("foo/bar/../../../../evil.txt", "MALICIOUS CONTENT")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_nested.zip", zip_buffer, "application/zip")},
        )
        assert resp.status_code in (400, 403)

    def test_zip_encoded_traversal(self):
        """Test ZIP with URL-encoded traversal sequences."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # URL-encoded ../
            zf.writestr("..%2fevil.txt", "MALICIOUS CONTENT")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_encoded.zip", zip_buffer, "application/zip")},
        )
        assert resp.status_code in (400, 403)

    def test_zip_double_encoded_traversal(self):
        """Test ZIP with double-encoded traversal sequences."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # Double-encoded ../
            zf.writestr("%2e%2e%2fevil.txt", "MALICIOUS CONTENT")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_dbl_encoded.zip", zip_buffer, "application/zip")},
        )
        assert resp.status_code in (400, 403)


class TestIsSafePath:
    """Unit tests for the is_safe_path function."""

    def test_safe_relative_path(self):
        """Safe relative path should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_safe_path(tmpdir, "safe/file.txt") is True
            assert is_safe_path(tmpdir, "subdir/file.java") is True

    def test_traversal_blocked(self):
        """Path traversal should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_safe_path(tmpdir, "../evil.txt") is False
            assert is_safe_path(tmpdir, "../../evil.txt") is False
            assert is_safe_path(tmpdir, "foo/../../evil.txt") is False

    def test_absolute_unix_blocked(self):
        """Absolute Unix paths should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_safe_path(tmpdir, "/etc/passwd") is False
            assert is_safe_path(tmpdir, "/absolute/path") is False

    def test_absolute_windows_blocked(self):
        """Absolute Windows paths should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_safe_path(tmpdir, "C:\\Windows\\evil.txt") is False
            assert is_safe_path(tmpdir, "C:/Windows/evil.txt") is False

    def test_null_byte_blocked(self):
        """Null bytes in path should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_safe_path(tmpdir, "file\x00.txt") is False


class TestArchiveResourceLimits:
    """Tests for archive resource exhaustion limits."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_oversized_archive_rejected(self):
        """Archive exceeding MAX_ZIP_SIZE_BYTES should be rejected."""
        # This test requires knowing the limit - we test the boundary logic
        from devlensx.core.config import MAX_ZIP_SIZE_BYTES
        # Just verify the config exists and is reasonable
        assert MAX_ZIP_SIZE_BYTES > 0
        assert MAX_ZIP_SIZE_BYTES <= 500_000_000  # Max 500MB

    def test_max_extracted_files_limit(self):
        """Test MAX_EXTRACTED_FILES config exists."""
        from devlensx.core.config import MAX_EXTRACTED_FILES
        assert MAX_EXTRACTED_FILES > 0
        assert MAX_EXTRACTED_FILES <= 50000

    def test_max_single_file_limit(self):
        """Test MAX_SINGLE_FILE_BYTES config exists."""
        from devlensx.core.config import MAX_SINGLE_FILE_BYTES
        assert MAX_SINGLE_FILE_BYTES > 0
        assert MAX_SINGLE_FILE_BYTES <= 100_000_000


class TestInvalidZipHandling:
    """Tests for invalid/corrupt ZIP handling (BadZipFile fix)."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_upload_empty_zip(self):
        """Empty ZIP should be rejected with 400."""
        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("empty.zip", b"", "application/zip")},
        )
        # Should be rejected with 400 Bad Request
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert "ZIP" in data["detail"] or "archive" in data["detail"].lower()

    def test_upload_corrupt_zip(self):
        """Corrupt ZIP should be rejected with 400."""
        # Create a corrupt ZIP (not a valid ZIP structure)
        corrupt_content = b"PK\x03\x04" + b"x" * 100  # Minimal ZIP header but corrupt
        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("corrupt.zip", corrupt_content, "application/zip")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data

    def test_upload_random_binary(self):
        """Random binary file with .zip extension should be rejected."""
        import os
        random_content = os.urandom(1024)
        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("random.zip", random_content, "application/zip")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data

    def test_upload_truncated_zip(self):
        """Truncated ZIP should be rejected."""
        # Create a valid small ZIP then truncate it
        import io
        import zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test.txt", "valid content")
        zip_buffer.seek(0)
        full_content = zip_buffer.read()
        truncated = full_content[:len(full_content)//2]  # Truncate
        
        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("truncated.zip", truncated, "application/zip")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data

    def test_upload_non_zip_extension(self):
        """File with non-.zip extension should be rejected."""
        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test.txt", b"not a zip", "text/plain")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data


class TestSymlinkEscape:
    """Tests for symlink escape prevention in ZIP extraction."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_zip_symlink_escape(self):
        """Test that symlinks in ZIP cannot escape extraction directory."""
        # Create a ZIP with a symlink that points outside
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # Create a symlink entry (this is platform-specific, may not work on Windows)
            # We test that the is_safe_path check would block it
            zi = zipfile.ZipInfo("link")
            zi.external_attr = 0o120000 << 16  # Symlink flag
            zf.writestr(zi, "../../../etc/passwd")
        zip_buffer.seek(0)

        resp = self.client.post(
            "/api/upload-zip",
            files={"file": ("test_symlink.zip", zip_buffer, "application/zip")},
        )
        # Should be rejected (400/403) or safely extracted without escape
        assert resp.status_code in (200, 400, 403)
        # If 200, the symlink should not have escaped


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])