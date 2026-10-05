"""
Git Security Tests (D10.2.8)

Tests for command injection prevention in git operations.
"""

import pytest
import tempfile
import os
from pathlib import Path

from devlensx.git.git_memory import GitMemoryEngine
from devlensx.services.git_service import GitService


@pytest.fixture(autouse=True)
def _restore_cwd():
    """These tests chdir into temp git repos; always restore the process CWD
    so later tests using repo-relative paths are unaffected."""
    prev = os.getcwd()
    try:
        yield
    finally:
        try:
            os.chdir(prev)
        except OSError:
            pass


class TestGitMemorySecurity:
    """Tests for GitMemoryEngine command injection prevention."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()

        # Initialize a git repo
        os.chdir(self.tmpdir)
        os.system("git init > /dev/null 2>&1")
        os.system("git config user.email 'test@test.com' > /dev/null 2>&1")
        os.system("git config user.name 'Test' > /dev/null 2>&1")

        # Create a test file
        test_file = self.repo_root / "test.java"
        test_file.write_text("public class Test {}", encoding="utf-8")

        os.system("git add . > /dev/null 2>&1")
        os.system("git commit -m 'initial' > /dev/null 2>&1")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_analyze_file_history_safe_path(self):
        """analyze_file_history should handle paths safely."""
        result = GitMemoryEngine.analyze_file_history(str(self.repo_root), "test.java")
        assert result["file"] == "test.java"
        assert "commit_count" in result

    def test_analyze_file_history_traversal_blocked(self):
        """Path traversal in file path should be handled safely."""
        # This should not crash or execute arbitrary commands
        result = GitMemoryEngine.analyze_file_history(str(self.repo_root), "../../etc/passwd")
        # Should return safe default for non-existent file
        assert result["file"] == "../../etc/passwd"
        assert result["commit_count"] == 0


class TestGitServiceSecurity:
    """Tests for GitService command injection prevention."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()

        # Initialize a git repo
        os.chdir(self.tmpdir)
        os.system("git init > /dev/null 2>&1")
        os.system("git config user.email 'test@test.com' > /dev/null 2>&1")
        os.system("git config user.name 'Test' > /dev/null 2>&1")

        # Create test files
        (self.repo_root / "test.java").write_text("public class Test {}", encoding="utf-8")
        (self.repo_root / "service.java").write_text("public class Service {}", encoding="utf-8")

        os.system("git add . > /dev/null 2>&1")
        os.system("git commit -m 'initial' > /dev/null 2>&1")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_file_churn_facts_safe(self):
        """get_file_churn_facts should handle file paths safely."""
        classes = [
            {"file": "test.java", "name": "Test"},
            {"file": "service.java", "name": "Service"},
        ]
        results = GitService.get_file_churn_facts(str(self.repo_root), classes)
        assert len(results) == 2
        for r in results:
            assert "file" in r
            assert "commit_count" in r

    def test_get_file_churn_facts_malicious_path(self):
        """Malicious file paths should be handled safely."""
        classes = [
            {"file": "../../etc/passwd", "name": "Evil"},
            {"file": "test.java; rm -rf /", "name": "Evil2"},
        ]
        # Should not crash or execute commands
        results = GitService.get_file_churn_facts(str(self.repo_root), classes)
        assert len(results) == 2
        for r in results:
            assert "file" in r


class TestGitCommandSafety:
    """Tests for git command construction safety."""

    def test_git_log_with_special_chars(self):
        """Git commands should handle special characters in paths safely."""
        # This tests that paths with special chars don't break git commands
        # ignore_cleanup_errors: Windows AV/indexer locks on fresh git dirs are
        # environmental; all security assertions run before teardown.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            repo_root = Path(tmpdir).resolve()
            os.chdir(tmpdir)
            os.system("git init > /dev/null 2>&1")
            os.system("git config user.email 'test@test.com' > /dev/null 2>&1")
            os.system("git config user.name 'Test' > /dev/null 2>&1")

            # File with spaces and special chars
            test_file = repo_root / "file with spaces.java"
            test_file.write_text("public class Test {}", encoding="utf-8")

            os.system("git add . > /dev/null 2>&1")
            os.system("git commit -m 'initial' > /dev/null 2>&1")

            result = GitMemoryEngine.analyze_file_history(str(repo_root), "file with spaces.java")
            assert result["file"] == "file with spaces.java"

    def test_git_log_with_unicode(self):
        """Git commands should handle unicode paths."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            repo_root = Path(tmpdir).resolve()
            os.chdir(tmpdir)
            os.system("git init > /dev/null 2>&1")
            os.system("git config user.email 'test@test.com' > /dev/null 2>&1")
            os.system("git config user.name 'Test' > /dev/null 2>&1")

            test_file = repo_root / "测试.java"
            test_file.write_text("public class Test {}", encoding="utf-8")

            os.system("git add . > /dev/null 2>&1")
            os.system("git commit -m 'initial' > /dev/null 2>&1")

            result = GitMemoryEngine.analyze_file_history(str(repo_root), "测试.java")
            assert result["file"] == "测试.java"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])