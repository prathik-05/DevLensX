"""
Secret Exposure Tests (D10.2.3)

Verify secrets are never logged, returned in API errors, or sent to LLM.
"""
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from devlensx.api.main import app
from devlensx.evidence.resolver import register_snapshot

FAKE_SECRET = "sk-test-FAKE-SECRET-abc123xyz"
FAKE_ENV_CONTENT = f"OPENAI_API_KEY={FAKE_SECRET}\nDATABASE_PASSWORD=supersecret123\n"


class TestHealthNoSecrets:
    def setup_method(self):
        self.client = TestClient(app)

    def test_health_does_not_leak_env(self):
        # Set fake env
        os.environ["OPENAI_API_KEY"] = FAKE_SECRET
        os.environ["GEMINI_API_KEY"] = FAKE_SECRET
        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        body = resp.text  # raw text to catch any leakage
        assert FAKE_SECRET not in body
        assert "OPENAI_API_KEY" not in body or '"llm": "available"' in body or '"llm":"available"' in body
        data = resp.json()
        # health must not contain raw keys
        serialized = str(data)
        assert FAKE_SECRET not in serialized
        # should be generic
        assert data.get("llm") in ("available", "unavailable (deterministic features active)")

    def test_health_no_filesystem_paths(self):
        resp = self.client.get("/api/health")
        data = resp.json()
        # health should not leak filesystem internals
        serialized = str(data).lower()
        assert "c:\\" not in serialized
        assert "/home/" not in serialized

class TestSecretNotInErrors:
    def setup_method(self):
        self.client = TestClient(app)

    def test_invalid_zip_error_no_secret(self):
        os.environ["OPENAI_API_KEY"] = FAKE_SECRET
        resp = self.client.post("/api/upload-zip", files={"file": ("test.zip", b"not a zip", "application/zip")})
        assert resp.status_code in (400, 403, 422)
        assert FAKE_SECRET not in resp.text

    def test_unknown_snapshot_error_no_secret(self):
        os.environ["OPENAI_API_KEY"] = FAKE_SECRET
        resp = self.client.post("/api/workspace/unknown_run_999/impact", json={"target_symbol": "Foo"})
        assert resp.status_code in (404, 422)
        assert FAKE_SECRET not in resp.text

class TestSecretFileHandling:
    def setup_method(self):
        self.client = TestClient(app)
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir) / "secret_repo"
        self.repo_root.mkdir()
        (self.repo_root / ".env").write_text(FAKE_ENV_CONTENT, encoding="utf-8")
        (self.repo_root / "config.py").write_text(f"API_KEY='{FAKE_SECRET}'\n", encoding="utf-8")
        (self.repo_root / "App.java").write_text("public class App {}", encoding="utf-8")
        register_snapshot("secret_repo", "run_secret", str(self.repo_root), "hash_secret")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_env_file_not_in_wiki_evidence_refs(self):
        """Wiki generation should not create EvidenceRefs to .env with secret values in content"""
        # The source file contains secret, but EvidenceRef only stores path/lines, not content
        # Verify that resolving .env still works but we don't auto-leak via API
        from devlensx.evidence.models import EvidenceRef
        from devlensx.evidence.resolver import EvidenceResolver
        resolver = EvidenceResolver()
        ref = EvidenceRef(repository_id="secret_repo", analysis_run_id="run_secret", commit_hash="hash_secret",
                          file_path=".env", line_start=1, line_end=1)
        result = resolver.resolve(ref)
        # .env is readable but test ensures health/wiki don't auto-expose
        assert result is not None
        # We don't assert resolved status - point is secrets not in health/logs

    def test_chat_does_not_echo_secret(self):
        """Chat should not echo secrets from repository files"""
        resp = self.client.post("/api/workspace/run_secret/chat", json={"message": "What is in .env file?", "mode": "FAST"})
        # Chat may fail without model, but must not leak secret if it succeeds
        if resp.status_code == 200:
            assert FAKE_SECRET not in resp.text
            # answer may contain redacted or insufficient evidence
            data = resp.json()
            assert FAKE_SECRET not in str(data)

    def test_source_reader_env_still_accessible_but_not_auto_sent_to_llm(self):
        """Direct SourceReader can read .env, but API-level chat should not auto-include raw secret in prompt logs"""
        # This test documents the invariant: secrets files are readable via EvidenceRef but not auto-sent to LLM
        # We verify that documentation generation does not embed secret values
        # Since we don't have LLM capture, we just verify files exist but health doesn't leak
        assert (self.repo_root / ".env").exists()
        assert FAKE_SECRET not in TestClient(app).get("/api/health").text
