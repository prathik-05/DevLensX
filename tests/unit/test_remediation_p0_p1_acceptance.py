"""
Acceptance Test Suite for P0 and P1 Remediation:
1. P0 — Repository snapshot isolation in copilot routes (no silent fallback to global_state).
2. P0 — Relationship preservation (IMPORTS and INJECTS never mislabeled as CALLS/VERIFIED_CALL).
3. P1 — Lexical matches marked as INFERRED with line-level citations (not spanning whole class).
4. P1 — Domain-aware regression suggestions (no game/winning templates on non-game symbols).
5. Additional Check A — Impact summary uses real measurements (no len*2, no dummy classes).
"""

import pytest
from fastapi.testclient import TestClient

from devlensx.api.main import app, global_state
from devlensx.evidence.models import SnapshotRecord
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.chat.orchestrator import _model_store, store_model
from devlensx.impact.analyzer import ImpactAnalyzer


client = TestClient(app)


class TestSnapshotIsolationCopilotRoutes:
    """Verifies that copilot routes strictly enforce snapshot isolation and never silently fall back to global_state."""

    def test_copilot_ask_fails_closed_on_unknown_run(self):
        # Set dummy data in global_state to verify it is NOT leaked
        global_state["repo_model"] = {"repo": "LeakedGlobalRepo", "classes": [{"name": "LeakedSecretClass"}]}
        
        response = client.post("/api/copilot/ask", json={
            "question": "What does this repo do?",
            "analysis_run_id": "non_existent_run_999"
        })
        assert response.status_code == 404
        assert "UNKNOWN_RUN:non_existent_run_999" in response.json()["detail"]
        assert "LeakedSecretClass" not in response.text

    def test_where_to_edit_fails_closed_on_unknown_run(self):
        global_state["repo_model"] = {"repo": "LeakedGlobalRepo", "classes": [{"name": "LeakedSecretClass"}]}
        
        response = client.post("/api/copilot/where-to-edit", json={
            "query": "add dark mode",
            "analysis_run_id": "non_existent_run_888"
        })
        assert response.status_code == 404
        assert "UNKNOWN_RUN:non_existent_run_888" in response.json()["detail"]

    def test_explain_concept_fails_closed_on_unknown_run(self):
        global_state["repo_model"] = {"repo": "LeakedGlobalRepo", "classes": [{"name": "LeakedSecretClass"}]}
        
        response = client.post("/api/copilot/explain-concept", json={
            "concept": "Authentication",
            "analysis_run_id": "non_existent_run_777"
        })
        assert response.status_code == 404
        assert "UNKNOWN_RUN:non_existent_run_777" in response.json()["detail"]

    def test_change_impact_fails_closed_on_unknown_run(self):
        global_state["repo_model"] = {"repo": "LeakedGlobalRepo", "classes": [{"name": "LeakedSecretClass"}]}
        
        response = client.get("/api/copilot/change-impact/OwnerController?analysis_run_id=non_existent_run_666")
        assert response.status_code == 404
        assert "UNKNOWN_RUN:non_existent_run_666" in response.json()["detail"]


class TestRelationshipPreservation:
    """Verifies that IMPORTS, INJECTS, and structural dependencies are never mislabeled as CALLS."""

    def test_imports_and_injects_never_mislabeled_as_calls(self):
        run_id = "test_run_relationship_typing"
        repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
        get_snapshot_registry().register("TestRepo", run_id, repo_path, "hash123")
        
        model = {
            "repo": "MyEnterpriseApp",
            "classes": [
                {"name": "AuthService", "file": "src/AuthService.java", "kind": "class", "stereotype": "Service"},
                {"name": "OrderController", "file": "src/OrderController.java", "kind": "class", "stereotype": "Controller"},
                {"name": "UserController", "file": "src/UserController.java", "kind": "class", "stereotype": "Controller"},
            ],
            "relationships": [
                {"source": "OrderController", "target": "AuthService", "type": "IMPORTS"},
                {"source": "UserController", "target": "AuthService", "type": "INJECTS"},
            ]
        }
        store_model(run_id, model)

        impact = ImpactAnalyzer.analyze("AuthService", run_id)
        assert impact.status == "OK"

        # IMPORTS and INJECTS must NOT be in direct_callers
        caller_syms = [dc["symbol"] for dc in impact.direct_callers]
        assert "OrderController" not in caller_syms
        assert "UserController" not in caller_syms

        # They must be preserved in dependencies
        dep_syms = {d["symbol"]: d["relation"] for d in impact.dependencies}
        assert dep_syms.get("OrderController") == "IMPORTS"
        assert dep_syms.get("UserController") == "INJECTS"
        for d in impact.dependencies:
            assert d["confidence"] == "VERIFIED_DEPENDENCY"


class TestLexicalMatchesAndLineCitations:
    """Verifies that text/regex matches are marked as INFERRED with exact line numbers."""

    def test_regex_calls_marked_inferred_with_exact_line(self):
        run_id = "test_run_tictactoe_citations"
        repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
        from devlensx.repository_memory import RepositoryIntelligenceEngine
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        get_snapshot_registry().register("TicTacToe", run_id, repo_path, "c0ffee1")
        store_model(run_id, intel.model)

        impact = ImpactAnalyzer.analyze("isTerminal", run_id)
        assert impact.status == "OK"

        # Verify direct callers found via AST/regex scanning have confidence=INFERRED and line-level citations
        for dc in impact.direct_callers:
            if dc.get("confidence") == "INFERRED":
                # Citation must point to an exact line #L<num>
                assert "#L" in dc["citation"]
                assert dc["line_start"] == dc["line_end"]
                assert dc["line_start"] > 0

        # Transitive callers must also have confidence=INFERRED and exact line citation
        for tc in impact.transitive_callers:
            assert tc.get("confidence") == "INFERRED"
            assert "#L" in tc["citation"]
            assert tc["line_start"] == tc["line_end"]


class TestDomainAwareRegressionSuggestions:
    """Verifies that generic symbols in non-game repos do not receive game/board templates."""

    def test_non_game_symbol_receives_no_game_templates(self):
        run_id = "test_run_non_game_domain"
        repo_path = "eval_repos/sp-portfolio"
        get_snapshot_registry().register("EnterpriseBilling", run_id, repo_path, "hash456")
        
        model = {
            "repo": "EnterpriseBillingService",
            "repo_summary": {"description": "Cloud billing and invoice processing platform"},
            "classes": [
                {
                    "name": "validateInvoice",
                    "file": "src/billing/InvoiceValidator.java",
                    "kind": "method",
                    "stereotype": "Service"
                }
            ],
            "relationships": []
        }
        store_model(run_id, model)

        impact = ImpactAnalyzer.analyze("validateInvoice", run_id)
        assert impact.status == "OK"

        # Must NOT contain game templates (horizontal, vertical, diagonal, winning line)
        all_text = " ".join(impact.potential_regressions + impact.recommended_validations).lower()
        assert "horizontal" not in all_text
        assert "diagonal" not in all_text
        assert "winning line" not in all_text
        assert "minimax" not in all_text

        # Must contain service-appropriate validation or honest disclosure
        assert any("business rule" in r.lower() or "method invariant" in r.lower() or "cannot be conclusively inferred" in r.lower() for r in (impact.potential_regressions + impact.recommended_validations))


class TestRealImpactMeasurementsAssistant:
    """Verifies that copilot/ask returns real measurements without multiplying or injecting dummy classes."""

    def test_no_matches_returns_zero_impact_and_no_dummy_classes(self):
        run_id = "test_run_impact_meas"
        repo_path = "eval_repos/sp-portfolio"
        get_snapshot_registry().register("TestMetrics", run_id, repo_path, "hash789")
        model = {
            "repo": "MetricsApp",
            "classes": [
                {"name": "DummyClassOne", "file": "src/Dummy1.java"},
                {"name": "DummyClassTwo", "file": "src/Dummy2.java"},
                {"name": "DummyClassThree", "file": "src/Dummy3.java"},
            ],
            "relationships": []
        }
        store_model(run_id, model)

        response = client.post("/api/copilot/ask", json={
            "question": "xyz123randomquestionnomatches",
            "analysis_run_id": run_id
        })
        assert response.status_code == 200
        data = response.json()
        
        # When no symbols match, affected_names must be empty, NOT filled with DummyClassOne, etc.
        assert data["affected_names"] == []
        assert data["impact"]["directly_affected"] == 0
        assert data["impact"]["potentially_affected"] == 0
        assert data["impact"]["affected_names"] == []
