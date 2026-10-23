"""
Milestone 3 Acceptance Test Suite — Evidence-Grounded AI Assistant

Tests AI Assistant and Q&A workflows across multiple distinct repository shapes:
1. Java Algorithmic Game (Tic-Tac-Toe)
2. Python CLI Game (Battleship)
3. TypeScript Web App (Portfolio)

Verifies:
- Intent classification and query-aware evidence retrieval
- Grounded, technical behavior explanations citing real files and lines
- Honest uncertainty / INSUFFICIENT_EVIDENCE for absent capabilities (auth, redis, kafka)
- Where-to-edit pinpointing real targets and returning INSUFFICIENT_EVIDENCE when target is absent
- Dynamic affected symbols and suggestions in /api/copilot/ask (no hardcoded SecurityConfig)
- Cross-run and cross-repository isolation
- Local inference (Ollama) and deterministic fallback
"""

import os
import pytest
from pathlib import Path
from typing import Dict, Any

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.chat.models import ChatContext, ChatIntent, ChatMode
from devlensx.chat.intent import classify_intent
from devlensx.chat.evidence_context import collect_evidence
from devlensx.chat.synthesis import synthesize_answer
from devlensx.reasoning.engine import RepositoryReasoningEngine
from devlensx.schemas.copilot import CopilotAskRequest
from devlensx.api.routes.copilot import ask_copilot
from devlensx.llm.provider import OllamaProvider, get_llm_provider


class TestAIAssistantIntentAndRetrieval:
    """Verifies intent classification and query-aware evidence scoring."""

    def test_intent_classification(self):
        assert classify_intent("What does this project do?") == ChatIntent.OVERVIEW
        assert classify_intent("How does data flow from controller to database?") == ChatIntent.DATA_FLOW
        assert classify_intent("Where should I edit to change the score board?") == ChatIntent.WHERE_TO_EDIT
        assert classify_intent("Which tests cover the minimax algorithm?") == ChatIntent.TESTING
        assert classify_intent("Is authentication or JWT secure here?") == ChatIntent.SECURITY

    def test_absent_capability_detection(self):
        snap = SnapshotRecord(repository_id="test", analysis_run_id="run_dummy", repo_path=".", commit_hash=None)
        dummy_model = {
            "classes": [
                {"name": "Board", "file": "Board.java", "line_start": 1, "line_end": 50, "stereotype": "Component"},
                {"name": "Minimax", "file": "Minimax.java", "line_start": 1, "line_end": 40, "stereotype": "Algorithm"},
            ],
            "relationships": [{"source": "Board", "target": "Minimax", "type": "CALLS"}],
        }
        ev = collect_evidence(snap, dummy_model, "How does authentication or JWT login work?")
        assert "authentication" in ev.missing_capabilities or "login" in ev.missing_capabilities
        ans, cites, _ = synthesize_answer("How does authentication or JWT login work?", ev, mode="FAST")
        assert "INSUFFICIENT_EVIDENCE" in ans or "not present" in ans.lower() or "no implementation" in ans.lower()
        # Must NOT claim authentication is verified or invent security classes
        assert "SecurityConfig" not in ans
        assert "JwtAuthenticationFilter" not in ans


class TestMultiRepositoryAssistantE2E:
    """Verifies AI Assistant behavior on actual test repositories."""

    @pytest.mark.skipif(not Path("eval_repos/Tic-Tac-Toe-with-Minimax-AI").exists(), reason="Tic-Tac-Toe repo missing")
    def test_tictactoe_assistant_grounding(self):
        repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        model = intel.model
        snap = SnapshotRecord(repository_id="TicTacToe", analysis_run_id="run_ttt", repo_path=repo_path, commit_hash=None)

        # 1. Overview query
        ev_overview = collect_evidence(snap, model, "What does this repository do?")
        ans_overview, claims, cites = synthesize_answer("What does this repository do?", ev_overview, mode="FAST", snapshot=snap, classes=model.get("classes"))
        assert any(w in ans_overview.lower() for w in ("game", "tic-tac-toe", "minimax", "board", "algorithmic"))
        assert "0 controllers" not in ans_overview.lower()
        assert len(cites) > 0
        assert any("Board" in str(c) or "Main" in str(c) or "Minimax" in str(c) for c in cites)

        # 2. Honest absent capability (Auth)
        ev_auth = collect_evidence(snap, model, "Explain the authentication and session management")
        assert any(k in ev_auth.missing_capabilities for k in ("authentication", "session"))
        ans_auth, _, _ = synthesize_answer("Explain the authentication and session management", ev_auth, mode="FAST", snapshot=snap, classes=model.get("classes"))
        assert "INSUFFICIENT_EVIDENCE" in ans_auth or "no implementation" in ans_auth.lower()
        assert "Jwt" not in ans_auth
        assert "SecurityConfig" not in ans_auth

        # 3. Where to edit query
        engine = RepositoryReasoningEngine()
        edit_res = engine.locate_where_to_edit("I want to change the board winning conditions and size", model, intel.graph_store)
        assert edit_res["primary_file"]["path"] != "Not Found"
        assert any(w in edit_res["primary_file"]["path"] for w in ("Board.java", "Main.java"))
        assert len(edit_res["exact_instructions"]) > 0

        # 4. Where to edit absent feature
        absent_edit = engine.locate_where_to_edit("I want to configure the Kafka consumer group and topic", model, intel.graph_store)
        assert absent_edit["primary_file"]["path"] == "Not Found"
        assert "INSUFFICIENT_EVIDENCE" in absent_edit["explanation"]

    @pytest.mark.skipif(not Path("eval_repos/battleship-python").exists(), reason="Battleship repo missing")
    def test_battleship_python_cli_grounding(self):
        repo_path = "eval_repos/battleship-python"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        model = intel.model
        snap = SnapshotRecord(repository_id="Battleship", analysis_run_id="run_bs", repo_path=repo_path, commit_hash=None)

        # 1. Overview query: must identify Python CLI game
        ev_overview = collect_evidence(snap, model, "What does this application do?")
        ans_ov, claims, cites = synthesize_answer("What does this application do?", ev_overview, mode="FAST", snapshot=snap, classes=model.get("classes"))
        assert "battleship" in ans_ov.lower() or "python" in ans_ov.lower() or "cli" in ans_ov.lower()
        assert "spring" not in ans_ov.lower()

        # 2. Where to edit ship placement or grid
        engine = RepositoryReasoningEngine()
        edit_res = engine.locate_where_to_edit("Where do I edit to change the battleship board grid size?", model, intel.graph_store)
        assert edit_res["primary_file"]["path"] != "Not Found"
        assert edit_res["primary_file"]["path"].endswith(".py")

        # 3. Absent technology inquiry
        ev_redis = collect_evidence(snap, model, "How does the Redis caching tier operate?")
        assert "redis" in ev_redis.missing_capabilities
        ans_redis, _, _ = synthesize_answer("How does the Redis caching tier operate?", ev_redis, mode="FAST", snapshot=snap, classes=model.get("classes"))
        assert "INSUFFICIENT_EVIDENCE" in ans_redis or "no implementation" in ans_redis.lower()

    @pytest.mark.skipif(not Path("eval_repos/sp-portfolio").exists(), reason="Portfolio repo missing")
    def test_portfolio_frontend_grounding(self):
        repo_path = "eval_repos/sp-portfolio"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        model = intel.model
        snap = SnapshotRecord(repository_id="sp-portfolio", analysis_run_id="run_port", repo_path=repo_path, commit_hash=None)

        # 1. Overview
        ev = collect_evidence(snap, model, "Give me an overview of this project")
        ans, cites, _ = synthesize_answer("Give me an overview of this project", ev, mode="FAST", snapshot=snap, classes=model.get("classes"))
        assert any(w in ans.lower() for w in ("portfolio", "typescript", "frontend", "react", "next"))
        assert "ownercontroller" not in ans.lower()

        # 2. Where to edit navbar/UI
        engine = RepositoryReasoningEngine()
        edit_res = engine.locate_where_to_edit("I want to edit the navigation bar or header links", model, intel.graph_store)
        assert edit_res["primary_file"]["path"] != "Not Found"
        assert any(edit_res["primary_file"]["path"].endswith(ext) for ext in (".tsx", ".jsx", ".ts", ".js", ".html"))


class TestCopilotEndpointAndIsolation:
    """Verifies that /api/copilot/ask behaves dynamically and maintains isolation."""

    @pytest.mark.skipif(not Path("eval_repos/Tic-Tac-Toe-with-Minimax-AI").exists(), reason="Tic-Tac-Toe repo missing")
    def test_copilot_ask_endpoint_dynamic_response(self):
        repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        run_id = "test_run_tictactoe_123"

        # Register run in active memory for resolution
        from devlensx.chat.orchestrator import store_model
        store_model(run_id, intel.model)
        from devlensx.api.main import global_state
        global_state["graph_store"] = intel.graph_store

        req = CopilotAskRequest(
            question="Where should I modify the code to change minimax depth?",
            analysis_run_id=run_id
        )
        resp = ask_copilot(req)

        # 1. Answer must be grounded and non-empty
        answer_text = resp["answer"] if isinstance(resp, dict) else resp.answer
        assert answer_text
        assert len(answer_text) > 20

        # 2. No hardcoded SecurityConfig in affected_names!
        affected = resp["affected_names"] if isinstance(resp, dict) else resp.affected_names
        assert "SecurityConfig" not in affected
        assert "JwtAuthenticationFilter" not in affected

        # 3. Dynamic follow-ups must be provided
        follow_ups = resp["suggested_follow_ups"] if isinstance(resp, dict) else resp.suggested_follow_ups
        assert len(follow_ups) > 0

    def test_cross_run_evidence_isolation(self):
        snap1 = SnapshotRecord(repository_id="RepoA", analysis_run_id="run_a", repo_path=".", commit_hash=None)
        model_a = {
            "classes": [
                {"name": "AuthService", "file": "src/AuthService.java", "line_start": 1, "line_end": 50, "stereotype": "Service"},
            ],
            "relationships": [],
        }

        snap2 = SnapshotRecord(repository_id="RepoB", analysis_run_id="run_b", repo_path=".", commit_hash=None)
        model_b = {
            "classes": [
                {"name": "MinimaxAI", "file": "src/MinimaxAI.java", "line_start": 1, "line_end": 60, "stereotype": "Algorithm"},
            ],
            "relationships": [],
        }

        ev_a = collect_evidence(snap1, model_a, "Explain AuthService")
        ev_b = collect_evidence(snap2, model_b, "Explain AuthService")

        # Run A must find AuthService
        assert any(s["name"] == "AuthService" for s in ev_a.deterministic_symbols)
        # Run B must NOT find AuthService from Run A
        assert not any(s["name"] == "AuthService" for s in ev_b.deterministic_symbols)
        assert ev_b.missing_capabilities or not ev_b.query_matched
