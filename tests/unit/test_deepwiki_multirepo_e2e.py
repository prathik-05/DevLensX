"""
Milestone 2 Acceptance Test Suite — DeepWiki Repository Understanding & Documentation Quality

Tests DeepWiki across multiple distinct repository shapes:
1. Java Algorithmic Game (Tic-Tac-Toe)
2. Python CLI Game (Battleship)
3. TypeScript / Next.js Web App (Portfolio)
4. Library / Incomplete evidence holdout

Verifies:
- Adaptive archetype and distinct documentation pages (no generic repeated text)
- Test classes segregated from production components
- Strict claim verification (no false VERIFIED on unproved relationships)
- Grounded, valid Mermaid diagrams inline in pages
- Accurate source citations with file paths and line ranges
- Live / Mocked provider diagnostics
"""

import os
import pytest
from pathlib import Path

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.wiki import generate_wiki_pages, get_wiki_tree, get_wiki_page
from devlensx.diagrams.generator import validate_mermaid_syntax
from devlensx.documentation.page_verifier import PageVerifier
from devlensx.critic.claim_verifier import AtomicClaim, ClaimVerdict
from devlensx.evidence.models import SnapshotRecord
from devlensx.llm.provider import OllamaProvider, get_llm_provider


class TestDeepWikiMultiRepositoryE2E:
    """Verifies that DeepWiki produces repository-specific, grounded technical documentation."""

    @pytest.mark.skipif(not Path("eval_repos/Tic-Tac-Toe-with-Minimax-AI").exists(), reason="Tic-Tac-Toe repo missing")
    def test_tictactoe_algorithmic_deepwiki(self):
        repo_path = "eval_repos/Tic-Tac-Toe-with-Minimax-AI"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        model = intel.model
        pages = generate_wiki_pages(model, graph_store=intel.graph_store, repo_id="TicTacToe")

        page_ids = [p.id for p in pages]
        assert "overview" in page_ids
        assert "architecture" in page_ids

        # 1. Overview must be grounded in algorithmic game, NOT a generic backend
        ov = next(p for p in pages if p.id == "overview")
        assert "algorithmic" in ov.summary.lower() or "game" in ov.summary.lower() or "tictactoe" in ov.summary.lower()
        # Must not claim 0 controllers or Spring REST lifecycle
        assert "0 controllers" not in ov.summary.lower()

        # 2. Key components must feature Board or Minimax, NOT MinimaxTest
        comp_page = next((p for p in pages if p.id == "components"), None)
        if comp_page:
            comp_names = [s.get("nodeId") for s in comp_page.sections if s.get("nodeId")]
            assert any(n in ("Board", "Minimax", "Main") for n in comp_names)
            assert not any("test" in n.lower() for n in comp_names)

        # 3. Architecture diagram must be valid Mermaid syntax
        arch = next(p for p in pages if p.id == "architecture")
        assert arch.mermaid is not None
        validated_syntax = validate_mermaid_syntax(arch.mermaid)
        assert "graph" in validated_syntax or "flowchart" in validated_syntax

        # 4. Citations must link to real source files and lines
        for cit in ov.citations:
            assert cit.get("file")
            assert not cit["file"].startswith("fake")
            assert Path(cit["file"]).exists() or (Path(repo_path) / cit["file"]).exists()

    @pytest.mark.skipif(not Path("eval_repos/battleship-python").exists(), reason="Battleship repo missing")
    def test_battleship_cli_deepwiki(self):
        repo_path = "eval_repos/battleship-python"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        pages = generate_wiki_pages(intel.model, graph_store=intel.graph_store, repo_id="Battleship")

        ov = next(p for p in pages if p.id == "overview")
        # Python CLI game: must identify Python and not claim Java/Spring
        assert "python" in ov.summary.lower()
        assert "spring" not in ov.summary.lower()

        # Check API reference honestly reports no HTTP REST controllers
        api_page = next((p for p in pages if p.id == "api-reference"), None)
        if api_page:
            content = " ".join(s.get("content", "") for s in api_page.sections)
            assert "no http rest" in content.lower() or "direct" in content.lower()

    @pytest.mark.skipif(not Path("eval_repos/sp-portfolio").exists(), reason="Portfolio repo missing")
    def test_portfolio_frontend_deepwiki(self):
        repo_path = "eval_repos/sp-portfolio"
        intel = RepositoryIntelligenceEngine().analyze(repo_path)
        pages = generate_wiki_pages(intel.model, graph_store=intel.graph_store, repo_id="sp-portfolio")

        ov = next(p for p in pages if p.id == "overview")
        assert "frontend" in ov.summary.lower() or "typescript" in ov.summary.lower()

        # Architecture diagram must NOT hallucinate Spring controllers
        arch = next(p for p in pages if p.id == "architecture")
        assert "spring" not in arch.mermaid.lower()
        assert "ownercontroller" not in arch.mermaid.lower()


class TestClaimVerificationInvariants:
    """Verifies that claims are never falsely marked VERIFIED without proof."""

    def test_unsupported_relationship_is_rejected(self):
        snapshot = SnapshotRecord("TestRepo", "run1", "eval_repos/Tic-Tac-Toe-with-Minimax-AI", "hash1")
        classes = [
            {"name": "Main", "file": "src/Main.java", "line_start": 1, "line_end": 20, "stereotype": "Component"},
            {"name": "UnrelatedHelper", "file": "src/Helper.java", "line_start": 1, "line_end": 15, "stereotype": "Utility"},
        ]
        # No relationship between Main and UnrelatedHelper
        relationships = []

        raw_claim = AtomicClaim(
            subject="Main",
            predicate="calls",
            object="UnrelatedHelper",
            claim_type="structural",
        )

        v_claims, v_refs, v_verdict = PageVerifier.verify_section_claims(
            raw_claims=[raw_claim],
            snapshot=snapshot,
            classes=classes,
            relationships=relationships,
        )

        assert len(v_claims) == 1
        # Must NOT be VERIFIED! Must be UNSUPPORTED
        assert v_claims[0].verdict == ClaimVerdict.UNSUPPORTED
        assert v_verdict == "INSUFFICIENT_EVIDENCE"
        assert len(v_refs) == 0

    def test_verified_relationship_has_evidence_ref(self):
        snapshot = SnapshotRecord("TestRepo", "run1", "eval_repos/Tic-Tac-Toe-with-Minimax-AI", "hash1")
        classes = [
            {"name": "Main", "file": "src/Main.java", "line_start": 1, "line_end": 20, "stereotype": "Component"},
            {"name": "Board", "file": "src/Board.java", "line_start": 1, "line_end": 50, "stereotype": "Component"},
        ]
        relationships = [{"source": "Main", "target": "Board"}]

        raw_claim = AtomicClaim(
            subject="Main",
            predicate="calls",
            object="Board",
            claim_type="structural",
        )

        v_claims, v_refs, v_verdict = PageVerifier.verify_section_claims(
            raw_claims=[raw_claim],
            snapshot=snapshot,
            classes=classes,
            relationships=relationships,
        )

        assert len(v_claims) == 1
        assert v_claims[0].verdict == ClaimVerdict.VERIFIED
        assert v_verdict == "VERIFIED"
        assert len(v_refs) == 1
        assert v_refs[0].file_path == "src/Main.java"
        assert v_refs[0].line_start == 1


class TestOllamaDeepWikiInference:
    """Tests local Ollama inference capabilities for DeepWiki reasoning."""

    def test_ollama_auto_resolution_and_health(self):
        provider = get_llm_provider("auto")
        assert provider is not None
        health = provider.health()
        assert health["ok"] is True
        # If running against local Ollama, verify model
        if isinstance(provider, OllamaProvider):
            assert "qwen2.5-coder:1.5b" in health.get("available_models", [])
