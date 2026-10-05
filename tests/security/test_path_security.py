"""
Path Security Tests - SourceReader & Path Validation (D10.2.3)

Tests the SourceReader bounds: traversal, symlinks, binary, size limits, missing files.
"""

import pytest
import tempfile
import os
from pathlib import Path

from devlensx.evidence.source_reader import SourceReader
from devlensx.evidence.models import (
    EvidenceRef,
    EvidenceType,
    ResolutionStatus,
    ResolvedEvidence,
)
from devlensx.core.security import is_safe_path


class TestSourceReaderPathValidation:
    """Tests for SourceReader._safe_target path validation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()
        self.reader = SourceReader(str(self.repo_root))

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_safe_relative_path(self):
        """Safe relative paths should resolve."""
        target = self.reader._safe_target("src/main/java/Foo.java")
        assert target is not None
        assert target.name == "Foo.java"

    def test_traversal_blocked(self):
        """Path traversal sequences should be blocked."""
        assert self.reader._safe_target("../evil.txt") is None
        assert self.reader._safe_target("../../evil.txt") is None
        assert self.reader._safe_target("foo/../../evil.txt") is None
        assert self.reader._safe_target("..\\evil.txt") is None  # Windows style

    def test_absolute_unix_blocked(self):
        """Absolute Unix paths should be blocked."""
        assert self.reader._safe_target("/etc/passwd") is None
        assert self.reader._safe_target("/absolute/path") is None

    def test_absolute_windows_blocked(self):
        """Absolute Windows paths should be blocked."""
        assert self.reader._safe_target("C:\\Windows\\evil.txt") is None
        assert self.reader._safe_target("C:/Windows/evil.txt") is None

    def test_null_byte_blocked(self):
        """Null bytes in path should be blocked."""
        assert self.reader._safe_target("file\x00.txt") is None

    def test_drive_letter_blocked(self):
        """Drive letters should be blocked."""
        assert self.reader._safe_target("D:evil.txt") is None

    def test_empty_path_blocked(self):
        """Empty paths should be blocked."""
        assert self.reader._safe_target("") is None
        assert self.reader._safe_target("   ") is None


class TestSourceReaderFileAccess:
    """Tests for SourceReader file access with actual files."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()
        self.reader = SourceReader(str(self.repo_root))

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_file(self, rel_path: str, content: str) -> Path:
        """Helper to write a file in the repo."""
        target = self.repo_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def test_valid_file_read(self):
        """Reading a valid file should succeed."""
        self._write_file("src/Foo.java", "public class Foo {}\n")
        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="src/Foo.java",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        assert result.resolved is True
        assert result.status == ResolutionStatus.RESOLVED
        assert len(result.lines) > 0
        assert "class Foo" in result.lines[0].content

    def test_missing_file(self):
        """Missing file should return FILE_NOT_FOUND."""
        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="src/Missing.java",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.FILE_NOT_FOUND

    def test_traversal_in_ref(self):
        """Traversal in EvidenceRef file_path should be blocked."""
        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="../../etc/passwd",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.PATH_VIOLATION

    def test_absolute_path_in_ref(self):
        """Absolute path in EvidenceRef should be blocked."""
        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="/etc/passwd",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.PATH_VIOLATION

    def test_file_too_large(self):
        """File exceeding MAX_FILE_BYTES should be rejected."""
        # Create a file larger than 1MB
        large_content = "x" * (1_000_001)  # Just over 1MB
        self._write_file("large.txt", large_content)

        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="large.txt",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.FILE_TOO_LARGE

    def test_binary_file_rejected(self):
        """Binary files should be rejected."""
        # Create a binary file
        binary_content = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE] * 100)
        target = self.repo_root / "binary.dat"
        target.write_bytes(binary_content)

        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="binary.dat",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.BINARY_FILE

    def test_symlink_escape_blocked(self):
        """Symlinks escaping repo root should be blocked."""
        # Create a file outside the repo
        outside_dir = Path(tempfile.mkdtemp())
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("SECRET")

        # Create symlink inside repo pointing outside
        symlink = self.repo_root / "link.txt"
        try:
            symlink.symlink_to(outside_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="link.txt",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        # Should be blocked as PATH_VIOLATION
        assert result.resolved is False
        assert result.status == ResolutionStatus.PATH_VIOLATION

        # Cleanup
        import shutil
        shutil.rmtree(outside_dir, ignore_errors=True)

    def test_symlink_inside_repo_allowed(self):
        """Symlinks staying inside repo should be allowed."""
        target_file = self._write_file("target.txt", "TARGET CONTENT")
        symlink = self.repo_root / "link.txt"
        try:
            symlink.symlink_to(target_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="link.txt",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        assert result.resolved is True
        assert "TARGET CONTENT" in result.lines[0].content

    def test_invalid_line_range(self):
        """Invalid line ranges should be rejected."""
        self._write_file("small.txt", "line1\nline2\n")

        # Line range too large
        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="small.txt",
            line_start=1,
            line_end=1000,  # Way beyond file
        )
        result = self.reader.read_range(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.INVALID_RANGE

        # End before start
        ref2 = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="small.txt",
            line_start=5,
            line_end=3,
        )
        result2 = self.reader.read_range(ref2)
        assert result2.resolved is False
        assert result2.status == ResolutionStatus.INVALID_RANGE

    def test_context_lines_bounded(self):
        """Context lines should be bounded by MAX_CONTEXT_LINES."""
        content = "\n".join([f"line {i}" for i in range(1000)])
        self._write_file("big.txt", content)

        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="big.txt",
            line_start=500,
            line_end=500,
        )
        result = self.reader.read_range(ref, context_lines=50)
        assert result.resolved is True
        # Should not exceed MAX_CONTEXT_LINES * 2
        assert len(result.lines) <= 800  # MAX_CONTEXT_LINES (400) * 2

    def test_empty_file(self):
        """Empty file should be handled."""
        self._write_file("empty.txt", "")

        ref = EvidenceRef(
            repository_id="test",
            analysis_run_id="run1",
            file_path="empty.txt",
            line_start=1,
            line_end=1,
        )
        result = self.reader.read_range(ref)
        assert result.resolved is True
        assert result.total_lines == 0


class TestBinaryDetection:
    """Tests for binary file detection."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()
        self.reader = SourceReader(str(self.repo_root))

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_text_file_not_binary(self):
        """Normal text files should not be detected as binary."""
        target = self.repo_root / "normal.txt"
        target.write_text("Hello world\n" * 100, encoding="utf-8")
        assert self.reader._looks_binary(target) is False

    def test_null_bytes_binary(self):
        """Files with null bytes should be detected as binary."""
        target = self.repo_root / "with_null.bin"
        target.write_bytes(b"Hello\x00world")
        assert self.reader._looks_binary(target) is True

    def test_high_nontext_ratio_binary(self):
        """Files with high non-text ratio should be detected as binary."""
        # Create content with >30% non-text bytes
        target = self.repo_root / "high_ratio.bin"
        content = b"H" + bytes([0x80, 0x81, 0x82]) * 100 + b"ello"
        target.write_bytes(content)
        assert self.reader._looks_binary(target) is True

    def test_empty_file_not_binary(self):
        """Empty files should not be binary."""
        target = self.repo_root / "empty.txt"
        target.write_bytes(b"")
        assert self.reader._looks_binary(target) is False


class TestIsSafePath:
    """Tests for the standalone is_safe_path function."""

    def test_safe_paths(self):
        """Safe paths should pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_safe_path(tmpdir, "safe/file.txt") is True
            assert is_safe_path(tmpdir, "subdir/nested.java") is True

    def test_traversal_blocked(self):
        """Path traversal should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_safe_path(tmpdir, "../evil.txt") is False
            assert is_safe_path(tmpdir, "foo/../../evil.txt") is False

    def test_absolute_blocked(self):
        """Absolute paths should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_safe_path(tmpdir, "/etc/passwd") is False
            assert is_safe_path(tmpdir, "C:\\Windows\\evil.txt") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])