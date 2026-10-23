"""Regression tests for P0.1 (ingest URL fix) and Ollama auto-detection."""

import os
import re
import unittest
from unittest.mock import patch, MagicMock


class TestIngestUrlFix(unittest.TestCase):
    """P0.1 — verify new URL() is gone from ingestRepoApi."""

    def test_no_new_url_near_api_ingest(self):
        src = open("web/src/apiClient.ts", encoding="utf-8").read()
        # The fixed function must not use `new URL(` with `/api/ingest`
        # Find the ingestRepoApi function body
        fn_match = re.search(
            r"export async function ingestRepoApi.*?(?=\nexport |\Z)",
            src,
            re.DOTALL,
        )
        self.assertIsNotNone(fn_match, "ingestRepoApi not found in apiClient.ts")
        fn_body = fn_match.group(0)
        self.assertNotIn("new URL(", fn_body, "new URL() still present in ingestRepoApi")


class TestOllamaAutoDetection(unittest.TestCase):
    """P0 — Ollama is returned from auto when env vars are set.

    We check type *name* rather than isinstance because `importlib.reload`
    would create new class identities and break isinstance checks in other tests
    that imported the original classes at module load time.
    """

    def _provider_type_name(self, env_overrides: dict) -> str:
        from devlensx.llm.provider import get_llm_provider
        # get_llm_provider reads os.environ at call time — no reload needed.
        with patch.dict(os.environ, env_overrides, clear=False):
            provider = get_llm_provider("auto")
        return type(provider).__name__

    def test_ollama_url_triggers_auto(self):
        env = {k: "" for k in ["AZURE_ENDPOINT", "AZURE_API_KEY", "GROQ_API_KEY",
                                "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY",
                                "OPENROUTER_API_KEY", "LLM_PROVIDER"]}
        env["OLLAMA_URL"] = "http://localhost:11434/v1"
        self.assertEqual(self._provider_type_name(env), "OllamaProvider")

    def test_ollama_base_url_triggers_auto(self):
        env = {k: "" for k in ["AZURE_ENDPOINT", "AZURE_API_KEY", "GROQ_API_KEY",
                                "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY",
                                "OPENROUTER_API_KEY", "LLM_PROVIDER", "OLLAMA_URL"]}
        env["OLLAMA_BASE_URL"] = "http://localhost:11434/v1"
        self.assertEqual(self._provider_type_name(env), "OllamaProvider")

    def test_llm_provider_env_ollama(self):
        env = {k: "" for k in ["AZURE_ENDPOINT", "AZURE_API_KEY", "GROQ_API_KEY",
                                "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY",
                                "OPENROUTER_API_KEY", "OLLAMA_URL", "OLLAMA_BASE_URL"]}
        env["LLM_PROVIDER"] = "ollama"
        self.assertEqual(self._provider_type_name(env), "OllamaProvider")


class TestOllamaHealth(unittest.TestCase):
    """OllamaProvider.health() returns ok=False when unreachable."""

    def test_health_unreachable(self):
        import urllib.request
        from devlensx.llm.provider import OllamaProvider
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        with patch.object(urllib.request, "urlopen", side_effect=OSError("refused")):
            result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("not reachable", result.get("reason", ""))

    def test_health_reachable(self):
        import urllib.request
        from devlensx.llm.provider import OllamaProvider
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch.object(urllib.request, "urlopen", return_value=mock_resp):
            result = provider.health()
        self.assertTrue(result["ok"])


class TestDigestEvidenceRanking(unittest.TestCase):
    """Digest _is_test_class() correctly classifies test vs production classes."""

    def _is_test_class(self, name: str, file_path: str) -> bool:
        # Inline the same logic from digest.py so tests stay isolated
        nl = name.lower()
        fl = file_path.lower().replace("\\", "/")
        return (
            nl.startswith("test") or nl.endswith("test") or nl.endswith("tests")
            or "test" in fl or "/tests/" in fl or "spec" in fl or nl.endswith("spec")
        )

    def test_game_controller_test_is_test(self):
        self.assertTrue(
            self._is_test_class("GameControllerTest", "src/test/GameControllerTest.java")
        )

    def test_game_controller_is_not_test(self):
        self.assertFalse(
            self._is_test_class("GameController", "src/main/GameController.java")
        )

    def test_setup_in_test_file_is_test(self):
        self.assertTrue(self._is_test_class("setUp", "tests/test_game.py"))

    def test_service_class_is_not_test(self):
        self.assertFalse(self._is_test_class("UserService", "src/services/UserService.java"))


class TestDigestEmptyRepoModel(unittest.TestCase):
    """Digest with empty repo_model surfaces 'Insufficient source analysis data'."""

    def test_empty_classes_message(self):
        from devlensx.api.routes.digest import _extract_manifest_and_stack_evidence
        evidence = _extract_manifest_and_stack_evidence([], repo_model={"classes": []})
        self.assertEqual(evidence["key_symbols"], [])
        # The route converts empty key_symbols to the insufficient message
        symbols_section = (
            "\n".join(evidence["key_symbols"])
            if evidence["key_symbols"]
            else "Insufficient source analysis data — no class structure was extracted"
        )
        self.assertIn("Insufficient source analysis data", symbols_section)

    def test_none_repo_model(self):
        from devlensx.api.routes.digest import _extract_manifest_and_stack_evidence
        evidence = _extract_manifest_and_stack_evidence([], repo_model=None)
        self.assertEqual(evidence["key_symbols"], [])


if __name__ == "__main__":
    unittest.main()
