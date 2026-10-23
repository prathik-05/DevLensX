"""
DevLensX Unit Tests: Universal Repository-Agnostic Profiler & Architecture Engine
Validates:
1. Test vs production file/symbol classification (protecting words like attestation.py).
2. Explainable evidence ranking across Java, Python CLI, TypeScript UI, and libraries.
3. Adaptive architecture diagram generation without fake Spring controllers.
4. Ollama health probing and model availability checks.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from devlensx.understanding.profiling.repository_profiler import (
    RepositoryProfiler,
    is_test_file_or_symbol,
    is_generated_or_vendored,
    classify_symbol_role,
    rank_symbols_explainable,
)
from devlensx.evidence.models import SnapshotRecord
from devlensx.diagrams.generator import DiagramGenerator


class TestTestClassification(unittest.TestCase):
    """Ensures test classifier is accurate and never misclassifies production words like attestation.py."""

    def test_real_test_paths_and_files(self):
        self.assertTrue(is_test_file_or_symbol("src/test/java/com/pratik/GameControllerTest.java"))
        self.assertTrue(is_test_file_or_symbol("eval_repos/battleship-python/test_game.py"))
        self.assertTrue(is_test_file_or_symbol("web/src/components/Button.test.tsx"))
        self.assertTrue(is_test_file_or_symbol("web/src/components/Modal.spec.ts"))
        self.assertTrue(is_test_file_or_symbol("pkg/math_test.go"))
        self.assertTrue(is_test_file_or_symbol("tests/unit/test_ingest.py"))
        self.assertTrue(is_test_file_or_symbol("conftest.py"))

    def test_production_files_with_test_substring_not_flagged(self):
        # Words containing 'test' must NOT be classified as test files
        self.assertFalse(is_test_file_or_symbol("src/main/java/com/example/attestation/AttestationService.java"))
        self.assertFalse(is_test_file_or_symbol("services/attestation.py"))
        self.assertFalse(is_test_file_or_symbol("models/contest.py"))
        self.assertFalse(is_test_file_or_symbol("utils/latest.py"))
        self.assertFalse(is_test_file_or_symbol("algorithms/fastest_path.py"))
        self.assertFalse(is_test_file_or_symbol("src/greatest_common_divisor.cpp"))
        self.assertFalse(is_test_file_or_symbol("src/main/java/com/pratik/tictactoe/Main.java"))
        self.assertFalse(is_test_file_or_symbol("src/main/java/com/pratik/tictactoe/controller/GameController.java"))
        self.assertFalse(is_test_file_or_symbol("src/main/java/com/pratik/tictactoe/engine/MinimaxEngine.java"))
        self.assertFalse(is_test_file_or_symbol("src/main/java/com/pratik/tictactoe/model/Board.java"))

    def test_vendored_and_generated_paths(self):
        self.assertTrue(is_generated_or_vendored("node_modules/react/index.js"))
        self.assertTrue(is_generated_or_vendored(".venv/lib/site-packages/fastapi/main.py"))
        self.assertTrue(is_generated_or_vendored("target/classes/Main.class"))
        self.assertTrue(is_generated_or_vendored("__pycache__/engine.cpython-313.pyc"))
        self.assertFalse(is_generated_or_vendored("src/main/java/Main.java"))


class TestMultiRepositoryRanking(unittest.TestCase):
    """Tests explainable ranking across 4 materially different repository architectures."""

    def test_java_algorithmic_game_ranking(self):
        """Tic-Tac-Toe: Main, GameController, MinimaxEngine, Board rank top; GameControllerTest is test fixture."""
        classes = [
            {"name": "GameControllerTest", "file": "src/test/java/com/pratik/tictactoe/controller/GameControllerTest.java", "kind": "class", "stereotype": "Test"},
            {"name": "MinimaxEngineTest", "file": "src/test/java/com/pratik/tictactoe/engine/MinimaxEngineTest.java", "kind": "class", "stereotype": "Test"},
            {"name": "Main", "file": "src/main/java/com/pratik/tictactoe/Main.java", "kind": "class"},
            {"name": "GameController", "file": "src/main/java/com/pratik/tictactoe/controller/GameController.java", "kind": "class"},
            {"name": "MinimaxEngine", "file": "src/main/java/com/pratik/tictactoe/engine/MinimaxEngine.java", "kind": "class"},
            {"name": "Board", "file": "src/main/java/com/pratik/tictactoe/model/Board.java", "kind": "class"},
        ]
        prod, tests = rank_symbols_explainable(classes, task="overview")
        prod_names = [p["name"] for p in prod]
        test_names = [t["name"] for t in tests]

        # Production symbols prioritized
        self.assertIn("Main", prod_names)
        self.assertIn("GameController", prod_names)
        self.assertIn("MinimaxEngine", prod_names)
        self.assertIn("Board", prod_names)
        self.assertEqual(prod[0]["name"], "Main")
        self.assertEqual(prod[0]["role"], "ENTRYPOINT")

        # Tests cleanly segregated
        self.assertIn("GameControllerTest", test_names)
        self.assertIn("MinimaxEngineTest", test_names)
        self.assertNotIn("GameControllerTest", prod_names)

    def test_python_cli_game_ranking(self):
        """Battleship: Game, AIPlayer, Ship rank top; TestShip, TestBoard are test fixtures."""
        classes = [
            {"name": "TestShip", "file": "test_game.py", "kind": "class"},
            {"name": "TestBoard", "file": "test_game.py", "kind": "class"},
            {"name": "AIPlayer", "file": "ai_player.py", "kind": "class"},
            {"name": "Game", "file": "game.py", "kind": "class"},
            {"name": "Ship", "file": "ship.py", "kind": "class"},
        ]
        prod, tests = rank_symbols_explainable(classes, task="overview")
        prod_names = [p["name"] for p in prod]
        test_names = [t["name"] for t in tests]

        self.assertIn("Game", prod_names)
        self.assertIn("AIPlayer", prod_names)
        self.assertIn("Ship", prod_names)
        self.assertIn("TestShip", test_names)
        self.assertIn("TestBoard", test_names)
        self.assertNotIn("TestShip", prod_names)

    def test_typescript_web_app_ranking(self):
        """Next.js / React: Layout, Pages, Components, and State Providers rank with no controllers/services needed."""
        classes = [
            {"name": "RootLayout", "file": "src/app/layout.tsx", "kind": "function"},
            {"name": "Home", "file": "src/app/page.tsx", "kind": "function"},
            {"name": "CardTwoPortfolio", "file": "src/components/card-two-portfolio.tsx", "kind": "function"},
            {"name": "SPDevProvider", "file": "src/context/spdev-provider.tsx", "kind": "function"},
        ]
        prod, tests = rank_symbols_explainable(classes, task="overview")
        prod_names = [p["name"] for p in prod]

        self.assertIn("RootLayout", prod_names)
        self.assertIn("Home", prod_names)
        self.assertIn("CardTwoPortfolio", prod_names)
        self.assertIn("SPDevProvider", prod_names)
        self.assertEqual(len(tests), 0)

    def test_library_without_entrypoints_produces_public_api(self):
        """A library (like AVL tree or math lib) identifies core exported modules and never claims empty."""
        classes = [
            {"name": "AvlTree", "file": "src/AvlTree.java", "kind": "class"},
            {"name": "AvlNode", "file": "src/AvlNode.java", "kind": "class"},
        ]
        profile = RepositoryProfiler.profile_repository(
            repo_path="eval_repos/AVL_Tree_Visualizer",
            classes=classes,
            repo_model={"classes": classes, "relationships": []}
        )
        self.assertIn(profile["archetype"], ("ALGORITHMIC_SYSTEM", "FRAMEWORK_LIBRARY", "MODULAR_APPLICATION"))
        self.assertTrue(len(profile["entry_points"]) >= 1)
        self.assertEqual(profile["entry_points"][0]["symbol"], "AvlTree")
        self.assertIn("Public Library Interface", profile["entry_points"][0]["type"])


class TestAgnosticDiagrams(unittest.TestCase):
    """Ensures Mermaid diagram generation adapts to repository archetype without hallucinating Spring controllers."""

    def test_algorithmic_system_diagram_layers(self):
        snap = SnapshotRecord(
            repository_id="tictactoe",
            analysis_run_id="run_ttt",
            repo_path="eval_repos/Tic-Tac-Toe-with-Minimax-AI",
            commit_hash="c1a2b3"
        )
        classes = [
            {"name": "Main", "file": "src/main/java/Main.java", "line_start": 1, "line_end": 20, "kind": "class"},
            {"name": "GameController", "file": "src/main/java/controller/GameController.java", "line_start": 1, "line_end": 50, "kind": "class"},
            {"name": "MinimaxEngine", "file": "src/main/java/engine/MinimaxEngine.java", "line_start": 1, "line_end": 80, "kind": "class"},
            {"name": "Board", "file": "src/main/java/model/Board.java", "line_start": 1, "line_end": 40, "kind": "class"},
        ]
        model = {"classes": classes, "relationships": [], "endpoints": []}
        gen = DiagramGenerator(snap, model)
        arch = gen.generate_architecture_diagram()

        self.assertIn("graph TD", arch.mermaid_source)
        self.assertIn("Main", arch.mermaid_source)
        self.assertIn("MinimaxEngine", arch.mermaid_source)
        self.assertIn("Board", arch.mermaid_source)
        arch.validate_invariants()

        # Data flow diagram
        df = gen.generate_data_flow_diagram()
        self.assertIn("graph LR", df.mermaid_source)
        self.assertTrue(len(df.nodes) >= 2)
        df.validate_invariants()


class TestOllamaHealthCheck(unittest.TestCase):
    """Validates Ollama reachability and model availability checks."""

    def test_ollama_health_checks_available_models(self):
        from devlensx.llm.provider import OllamaProvider
        p = OllamaProvider(base_url="http://localhost:11434/v1", model="qwen2.5-coder:7b")

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"models": [{"name": "qwen2.5-coder:7b"}, {"name": "llama3:latest"}]}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            health = p.health()
            self.assertTrue(health["ok"])
            self.assertTrue(health["model_available"])
            self.assertEqual(health["selected_model"], "qwen2.5-coder:7b")

    def test_ollama_health_reports_missing_model_honestly(self):
        from devlensx.llm.provider import OllamaProvider
        p = OllamaProvider(base_url="http://localhost:11434/v1", model="qwen2.5-coder:7b")

        mock_resp = MagicMock()
        # Tags only has qwen-9b:latest
        mock_resp.read.return_value = b'{"models": [{"name": "qwen-9b:latest"}]}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            health = p.health()
            self.assertTrue(health["ok"])
            self.assertFalse(health["model_available"])
            self.assertIn("not found in local Ollama", health["reason"])


if __name__ == "__main__":
    unittest.main()
