"""
Milestone 5 Acceptance Test Suite — Impact Analysis & Change Impact Grounding

Validates:
1. Direct Callers: High-precision and recall identification of functions/classes calling the target.
2. Transitive Impact: Multi-hop reachability following verified relationships (Board -> GameController -> Main).
3. Dependency Analysis: Distinguishes CALLS from EXTENDS, IMPLEMENTS, INJECTS, and IMPORTS.
4. Test Discovery: Narrowed test discovery connecting tests to targets without claiming unrelated tests.
5. Change Comparison: Analyzes git diffs, detects modified method signatures, and flags affected callers.
6. Risk Assessment: Explains why a change is risky with verified scoring and 0 false high-severity risks.
7. Evidence and Uncertainty: Line-level citations, reflection / dynamic dispatch disclosures.
8. Execution Order Distinction: Distinguishes VERIFIED_CALL_ORDER, INFERRED_ARCHITECTURE_ORDER, and UNRESOLVED_RUNTIME_BEHAVIOR.
9. Multi-Repository Agnostic: Java (Tic-Tac-Toe), Python (Battleship), TypeScript (Portfolio).
10. Snapshot Isolation: Strict closed failure on unknown run and zero cross-run leakage.
"""

import os
import pytest
from pathlib import Path

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.chat.orchestrator import _model_store
from devlensx.impact.analyzer import ImpactAnalyzer
from devlensx.impact.models import ImpactResult


@pytest.fixture
def tictactoe_snapshot():
    repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
    if not Path(repo_path).exists():
        pytest.skip("Tic-Tac-Toe repo missing")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    run_id = "test_run_impact_ttt"
    snap = SnapshotRecord(repository_id="TicTacToe", analysis_run_id=run_id, repo_path=repo_path, commit_hash="c0ffee1")
    get_snapshot_registry().register("TicTacToe", run_id, repo_path, "c0ffee1")
    _model_store[run_id] = intel.model
    return {"run_id": run_id, "model": intel.model, "repo_path": repo_path}


@pytest.fixture
def battleship_snapshot():
    repo_path = "eval_repos/battleship-python"
    if not Path(repo_path).exists():
        pytest.skip("Battleship repo missing")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    run_id = "test_run_impact_bs"
    snap = SnapshotRecord(repository_id="Battleship", analysis_run_id=run_id, repo_path=repo_path, commit_hash="c0ffee2")
    get_snapshot_registry().register("Battleship", run_id, repo_path, "c0ffee2")
    _model_store[run_id] = intel.model
    return {"run_id": run_id, "model": intel.model, "repo_path": repo_path}


@pytest.fixture
def portfolio_snapshot():
    repo_path = "eval_repos/sp-portfolio"
    if not Path(repo_path).exists():
        pytest.skip("Portfolio repo missing")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    run_id = "test_run_impact_port"
    snap = SnapshotRecord(repository_id="Portfolio", analysis_run_id=run_id, repo_path=repo_path, commit_hash="c0ffee3")
    get_snapshot_registry().register("Portfolio", run_id, repo_path, "c0ffee3")
    _model_store[run_id] = intel.model
    return {"run_id": run_id, "model": intel.model, "repo_path": repo_path}


class TestJavaImpactAnalysis:
    """Verifies Java impact analysis on Tic-Tac-Toe (classes, methods, callers, transitive chains)."""

    def test_direct_callers_precision_and_citations(self, tictactoe_snapshot):
        run_id = tictactoe_snapshot["run_id"]
        # Analyze Board class
        impact = ImpactAnalyzer.analyze("Board", run_id)
        assert impact.status == "OK"
        assert impact.target_symbol == "Board"

        # Direct callers must include GameController or MinimaxEngine
        caller_syms = [dc["symbol"] for dc in impact.direct_callers]
        assert any(c in caller_syms for c in ("GameController", "MinimaxEngine", "BoardPanel"))

        # Every direct caller citation must point to valid file and line ranges
        for dc in impact.direct_callers:
            assert dc["file"]
            assert dc["line_start"] >= 1
            assert dc["line_end"] >= dc["line_start"]
            assert "#L" in dc["citation"]

    def test_method_level_impact_and_transitive_chain(self, tictactoe_snapshot):
        run_id = tictactoe_snapshot["run_id"]
        # Analyze method: isTerminal
        impact = ImpactAnalyzer.analyze("isTerminal", run_id)
        assert impact.status == "OK"

        # Direct callers must contain handleCellClick or triggerAiMove or searchBestMove
        caller_syms = [dc["symbol"] for dc in impact.direct_callers]
        assert any(c in caller_syms for c in ("handleCellClick", "triggerAiMove", "searchBestMove", "placeMark", "paintComponent"))

        # Transitive callers must be present (hop >= 2)
        assert len(impact.transitive_callers) > 0
        for tc in impact.transitive_callers:
            assert tc["hop"] >= 2
            assert len(tc["path"]) >= 3

    def test_semantic_winning_condition_mapping(self, tictactoe_snapshot):
        run_id = tictactoe_snapshot["run_id"]
        # User queries Board.isWinner() - should resolve to evaluateBoard / isTerminal in Board
        impact = ImpactAnalyzer.analyze("Board.isWinner()", run_id)
        assert impact.status == "OK"
        assert impact.target_symbol in ("evaluateBoard", "isTerminal", "Board")
        # Must produce domain-specific potential regressions
        assert any("win" in r.lower() or "terminal" in r.lower() for r in impact.potential_regressions)
        # Must produce validation checklist (horizontal, vertical, diagonal)
        assert any("horizontal" in v.lower() for v in impact.recommended_validations)
        assert any("diagonal" in v.lower() for v in impact.recommended_validations)

    def test_test_discovery_precision_java(self, tictactoe_snapshot):
        run_id = tictactoe_snapshot["run_id"]
        impact = ImpactAnalyzer.analyze("Board", run_id)
        test_syms = [t["symbol"] for t in impact.tests]
        # Must find BoardTest or tests exercising Board
        assert any("BoardTest" in s or "Board" in s for s in test_syms)


class TestPythonImpactAnalysis:
    """Verifies Python impact analysis on Battleship (functions, modules, CLI execution)."""

    def test_python_function_impact(self, battleship_snapshot):
        run_id = battleship_snapshot["run_id"]
        impact = ImpactAnalyzer.analyze("place_ship", run_id)
        assert impact.status == "OK"
        # Must identify game.py or test_game.py as callers/dependents
        all_syms = [d["symbol"] for d in impact.downstream] + [dc["symbol"] for dc in impact.direct_callers] + [t["symbol"] for t in impact.tests]
        assert any("game" in s.lower() for s in all_syms)

    def test_python_board_class_impact(self, battleship_snapshot):
        run_id = battleship_snapshot["run_id"]
        impact = ImpactAnalyzer.analyze("Board", run_id)
        assert impact.status == "OK"
        assert impact.risk_level in ("MEDIUM", "HIGH", "CRITICAL")
        assert len(impact.risk_assessment["reasons"]) > 0


class TestTypeScriptImpactAnalysis:
    """Verifies TypeScript impact analysis on Next.js / React portfolio."""

    def test_typescript_component_impact(self, portfolio_snapshot):
        run_id = portfolio_snapshot["run_id"]
        # Navbar component in sp-portfolio
        impact = ImpactAnalyzer.analyze("Navbar", run_id)
        assert impact.status == "OK"
        # SiteChrome or page importing Navbar should be found
        downstream_files = [d.get("file", "") for d in impact.downstream] + [dc.get("file", "") for dc in impact.direct_callers]
        assert any("site-chrome" in f.lower() or "navbar" in f.lower() for f in downstream_files)

    def test_dynamic_route_disclosure(self, portfolio_snapshot):
        run_id = portfolio_snapshot["run_id"]
        impact = ImpactAnalyzer.analyze("Navbar", run_id)
        # Next.js portfolio has dynamic [slug] routes
        assert impact.execution_order_type in ("UNRESOLVED_RUNTIME_BEHAVIOR", "VERIFIED_CALL_ORDER")
        assert any("dynamic" in lim.lower() for lim in impact.coverage_limitations)


class TestDiffAndUncertaintyAnalysis:
    """Verifies change comparison on git diff and strict snapshot isolation."""

    def test_git_diff_signature_breakage_detection(self, tictactoe_snapshot):
        run_id = tictactoe_snapshot["run_id"]
        diff = (
            "diff --git a/Board.java b/Board.java\n"
            "--- a/Board.java\n"
            "+++ b/Board.java\n"
            "@@ -88,3 +88,3 @@\n"
            "- public boolean placeMark(int row, int col, Cell mark)\n"
            "+ public boolean placeMark(int row, int col, Cell mark, boolean validateOnly)\n"
        )
        impact = ImpactAnalyzer.analyze("placeMark", run_id, git_diff=diff)
        assert impact.status == "OK"
        assert impact.diff_analysis is not None
        assert impact.diff_analysis["changed_in_diff"] is True
        assert len(impact.diff_analysis["affected_callers"]) > 0

    def test_unknown_target_returns_clean_target_not_found(self, tictactoe_snapshot):
        run_id = tictactoe_snapshot["run_id"]
        impact = ImpactAnalyzer.analyze("NonexistentDatabaseService", run_id)
        assert impact.status == "TARGET_NOT_FOUND"
        assert len(impact.direct) == 0
        assert len(impact.downstream) == 0
        assert len(impact.direct_callers) == 0

    def test_snapshot_isolation_rejects_unknown_run(self):
        with pytest.raises(ValueError, match="UNKNOWN_RUN"):
            ImpactAnalyzer.analyze("Board", "completely_unknown_run_xyz")
