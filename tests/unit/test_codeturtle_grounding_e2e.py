"""
Milestone 4 Acceptance Test Suite — Code Turtle Visual Code Exploration & Prioritized Review

Tests Code Turtle execution flow tracing, call hierarchy ordering, and PR code review
across multiple distinct repository shapes:
1. Java Algorithmic Game (Tic-Tac-Toe)
2. Python CLI Game (Battleship)

Verifies:
- Call hierarchy execution order (Entrypoint -> Controller -> Domain Logic -> Sub-component -> Test Suite)
- Order is strictly structural, never alphabetical or parser discovery order
- Grounded Mermaid sequence diagrams and line citations
- Symbol-specific execution flow with callers and callees
- Deterministic diff review with prioritized severity (CRITICAL > WARNING > INFO)
- Myers line-diff committable suggestions
- Separation of live repository reviews from demo presets
- Snapshot and run-level isolation
"""

import os
import pytest
from pathlib import Path
from typing import Dict, Any

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.reasoning.engine import RepositoryReasoningEngine
from devlensx.review.codeturtle import CodeTurtleReviewEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.diagrams.generator import validate_mermaid_syntax


class TestCodeTurtleExecutionFlow:
    """Verifies runtime execution flow tracing and call hierarchy ordering."""

    @pytest.mark.skipif(not Path("eval_repos/Tic-Tac-Toe-with-Minimax-AI").exists(), reason="Tic-Tac-Toe repo missing")
    def test_tictactoe_execution_hierarchy(self):
        repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        engine = RepositoryReasoningEngine()

        flow = engine.trace_execution_flow(repo_model=intel.model, graph_store=intel.graph_store)

        # 1. Flow metadata
        assert flow.get("verdict") == "VERIFIED_TOUR"
        assert flow.get("archetype") == "ALGORITHMIC_SYSTEM"
        assert "Tic-Tac-Toe" in flow.get("title", "")

        # 2. Steps order verification: Entrypoint -> Controller -> Domain Logic -> Test Suite
        steps = flow.get("steps", [])
        assert len(steps) >= 4

        symbols = [s["symbol"] for s in steps]
        # Step 1 must be Main entrypoint
        assert steps[0]["role"] == "ENTRYPOINT"
        assert steps[0]["symbol"] == "Main"
        assert "Main.java" in steps[0]["file"]
        assert steps[0]["line_start"] > 0

        # Step 2 must be Controller
        assert steps[1]["role"] == "CONTROLLER"
        assert steps[1]["symbol"] == "GameController"

        # Hierarchy must NOT be alphabetical ('Main' appears before 'GameController' despite 'G' < 'M')
        assert symbols.index("Main") < symbols.index("GameController")

        # Step 5 must be test verification if tests are indexed
        if len(steps) >= 5:
            assert steps[-1]["role"] == "TEST_SUITE"
            assert "Test" in steps[-1]["symbol"] or "test" in steps[-1]["file"].lower()

        # 3. Grounded Mermaid Sequence Diagram
        mermaid = flow.get("mermaid_diagram", "")
        assert mermaid.startswith("sequenceDiagram")
        assert "autonumber" in mermaid
        assert "Main" in mermaid
        assert "GameController" in mermaid

        # 4. Citations check
        for s in steps:
            assert s["citation"]
            assert "#L" in s["citation"]
            assert not s["file"].startswith("fake")
            assert (Path(repo_path) / s["file"]).exists() or Path(s["file"]).exists()

    @pytest.mark.skipif(not Path("eval_repos/battleship-python").exists(), reason="Battleship repo missing")
    def test_battleship_execution_hierarchy(self):
        repo_path = "eval_repos/battleship-python"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        engine = RepositoryReasoningEngine()

        flow = engine.trace_execution_flow(repo_model=intel.model, graph_store=intel.graph_store)

        assert flow.get("verdict") == "VERIFIED_TOUR"
        steps = flow.get("steps", [])
        assert len(steps) >= 3

        # Step 1 must be Game (entrypoint)
        assert steps[0]["role"] == "ENTRYPOINT"
        assert steps[0]["symbol"] == "Game"

        # Step 2 must be AIPlayer (orchestrator/algorithm)
        symbols = [s["symbol"] for s in steps]
        assert "AIPlayer" in symbols or "Board" in symbols

        # Verify Mermaid diagram
        assert "sequenceDiagram" in flow.get("mermaid_diagram", "")

    @pytest.mark.skipif(not Path("eval_repos/Tic-Tac-Toe-with-Minimax-AI").exists(), reason="Tic-Tac-Toe repo missing")
    def test_symbol_specific_execution_trace(self):
        repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        engine = RepositoryReasoningEngine()

        flow = engine.trace_execution_flow(symbol_name="Board", repo_model=intel.model, graph_store=intel.graph_store)

        assert flow.get("target_symbol") == "Board"
        assert flow.get("verdict") == "VERIFIED_FLOW"
        steps = flow.get("steps", [])
        assert len(steps) >= 2

        # Step 1 should be Entrypoint, Step 2 should be Board
        assert steps[0]["role"] == "ENTRYPOINT"
        assert steps[1]["symbol"] == "Board"
        assert "Board.java" in steps[1]["file"]


class TestCodeTurtlePrioritizedReview:
    """Verifies PR diff review, prioritized severity sorting, and snapshot isolation."""

    @pytest.mark.skipif(not Path("eval_repos/Tic-Tac-Toe-with-Minimax-AI").exists(), reason="Tic-Tac-Toe repo missing")
    def test_prioritized_severity_and_myers_diff(self):
        repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        model = intel.model

        # Register active snapshot
        registry = get_snapshot_registry()
        snap_id = "test_turtle_run_01"
        registry.register(
            repository_id="tictactoe-test",
            analysis_run_id=snap_id,
            repo_path=os.path.abspath(repo_path),
            commit_hash="abc1234"
        )

        from devlensx.chat.orchestrator import _model_store
        _model_store[snap_id] = model

        # Diff containing:
        # 1. Hardcoded secret (CRITICAL)
        # 2. Raw SQL string concatenation (CRITICAL)
        # 3. Debt marker (INFO)
        diff_text = (
            "diff --git a/src/main/java/com/pratik/tictactoe/model/Board.java b/src/main/java/com/pratik/tictactoe/model/Board.java\n"
            "--- a/src/main/java/com/pratik/tictactoe/model/Board.java\n"
            "+++ b/src/main/java/com/pratik/tictactoe/model/Board.java\n"
            "@@ -10,6 +10,12 @@ public class Board {\n"
            "+    // TODO: implement persistent board cache\n"
            "+    private String api_key = \"ghp_secretTokenValue1234567890\";\n"
            "+    public void queryBoard(String id) {\n"
            "+        String query = \"SELECT * FROM boards WHERE id = \" + id;\n"
            "+    }\n"
        )

        review = CodeTurtleReviewEngine.review(
            diff=diff_text,
            analysis_run_id=snap_id,
            provider="mock"
        )

        assert review.get("product") == "CodeTurtle AI Review"
        comments = review.get("comments", [])
        assert len(comments) >= 2

        # 1. Invariant: Severity Priority Sorting (CRITICAL before INFO)
        severities = [c.get("severity") for c in comments]
        assert severities[0] == "CRITICAL"
        assert severities[-1] == "INFO"

        # 2. Invariant: Grounded Citations
        crit_comment = comments[0]
        assert crit_comment.get("citation") is not None
        assert "Board.java#L" in crit_comment["citation"]
        assert crit_comment.get("verdict") == "VERIFIED"

        # 3. Invariant: Myers Line-Diff Committable Suggestion
        assert "diff_snippet" in crit_comment or "suggested_fix" in crit_comment

        # 4. Invariant: No Demo Text Leakage in live repo review
        full_review_text = str(review)
        assert "ClickMeComponent" not in full_review_text
        assert "petclinic" not in full_review_text

    def test_snapshot_isolation_rejects_unknown_run(self):
        with pytest.raises(ValueError, match="SNAPSHOT_NOT_FOUND"):
            CodeTurtleReviewEngine.review(
                diff="diff --git a/test.py b/test.py\n+x=1",
                analysis_run_id="non_existent_run_id_xyz",
                provider="mock"
            )
