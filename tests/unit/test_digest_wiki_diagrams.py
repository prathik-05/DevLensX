"""
Dedicated Regression Suite: Repository Digest, DeepWiki & UML Diagrams Reliability
Validates that:
1. Repository Digest binds directly to active snapshot, extracts manifests and entrypoints.
2. DeepWiki generates grounded conditional pages (Architecture, Workflows, APIs, Persistence, Security) with honest diagnostics.
3. UML Diagrams produce validated Mermaid syntax, sanitized IDs, and AI-annotated descriptions without graph hallucination.
4. AI Providers (Google AI Studio & OpenAI) load keys, handle fallbacks, and never expose secrets in errors.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from devlensx.evidence.models import SnapshotRecord, EvidenceRef, EvidenceType
from devlensx.evidence.resolver import get_snapshot_registry, register_snapshot
from devlensx.diagrams.generator import (
    DiagramGenerator,
    _sanitize_mermaid_id,
    _escape_mermaid_label,
    validate_mermaid_syntax,
    get_diagram_store,
)
from devlensx.diagrams.models import DiagramType
from devlensx.documentation.page_generator import DocumentationPageGenerator
from devlensx.documentation.models import PageStatus
from devlensx.llm.provider import (
    GeminiProvider,
    OpenAIProvider,
    OfflineProvider,
    get_llm_provider,
    _safe_error,
)
from devlensx.api.routes.digest import (
    _extract_manifest_and_stack_evidence,
    _run_ingest,
    DigestRequest,
    create_digest,
)


@pytest.fixture
def sample_snapshot(tmp_path: Path):
    registry = get_snapshot_registry()
    run_id = f"test_run_{os.urandom(4).hex()}"
    src_dir = tmp_path / "sample_app"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    # Write sample manifests and files
    (src_dir / "pom.xml").write_text("<project><modelVersion>4.0.0</modelVersion></project>", encoding="utf-8")
    (src_dir / "package.json").write_text('{"name": "test-app", "version": "1.0.0"}', encoding="utf-8")
    (src_dir / "main.py").write_text("print('hello world')", encoding="utf-8")

    snap = register_snapshot(
        repository_id="sample-service",
        analysis_run_id=run_id,
        repo_path=str(src_dir),
        commit_hash="c0ffee123456",
    )
    return snap


@pytest.fixture
def sample_repo_model(sample_snapshot: SnapshotRecord):
    return {
        "repo": "sample-service",
        "repo_path": sample_snapshot.repo_path,
        "repo_summary": {"language": "Java", "framework": "Spring Boot"},
        "classes": [
            {
                "name": "OrderController",
                "kind": "class",
                "stereotype": "Controller",
                "file": "src/OrderController.java",
                "line_start": 10,
                "line_end": 45,
            },
            {
                "name": "OrderService",
                "kind": "class",
                "stereotype": "Service",
                "file": "src/OrderService.java",
                "line_start": 12,
                "line_end": 55,
            },
            {
                "name": "OrderRepository",
                "kind": "interface",
                "stereotype": "Repository",
                "file": "src/OrderRepository.java",
                "line_start": 8,
                "line_end": 30,
            },
            {
                "name": "Order",
                "kind": "class",
                "stereotype": "Entity",
                "file": "src/Order.java",
                "line_start": 5,
                "line_end": 40,
            },
        ],
        "relationships": [
            {"source": "OrderController", "target": "OrderService", "type": "DEPENDS_ON"},
            {"source": "OrderService", "target": "OrderRepository", "type": "DEPENDS_ON"},
        ],
        "endpoints": [
            {"method": "POST", "route": "/api/orders", "handler": "createOrder", "file": "src/OrderController.java"},
            {"method": "GET", "route": "/api/orders/{id}", "handler": "getOrder", "file": "src/OrderController.java"},
        ],
    }


# ===========================================================================
# 1. Repository Digest Tests
# ===========================================================================

def test_extract_manifests_and_entrypoints():
    files = [
        {"path": "backend/pom.xml"},
        {"path": "frontend/package.json"},
        {"path": "scripts/main.py"},
        {"path": "deploy/Dockerfile"},
    ]
    model = {
        "endpoints": [{"method": "GET", "route": "/api/health", "handler": "healthCheck", "file": "app.py"}],
        "classes": [{"name": "HealthController", "stereotype": "Controller", "file": "app.py", "line_start": 1, "line_end": 20}],
    }
    extracted = _extract_manifest_and_stack_evidence(files, repo_model=model)
    assert any("pom.xml" in m for m in extracted["manifests"])
    assert any("package.json" in m for m in extracted["manifests"])
    assert any("Dockerfile" in m for m in extracted["manifests"])
    assert any("/api/health" in e for e in extracted["entrypoints"])
    assert len(extracted["key_symbols"]) >= 1


def test_digest_execution_with_snapshot_context(sample_snapshot: SnapshotRecord, sample_repo_model):
    res = _run_ingest(
        source=sample_snapshot.repo_path,
        analysis_run_id=sample_snapshot.analysis_run_id,
        repo_model=sample_repo_model,
    )
    assert res["success"] is True
    assert "pom.xml" in res["prompt_digest"]
    assert "package.json" in res["prompt_digest"]
    assert "## 1. Executive Overview" in res["prompt_digest"]
    assert "## 2. Detected Manifests & Tech Stack" in res["prompt_digest"]
    assert "## 3. Key Entry Points & Grounded Symbols" in res["prompt_digest"]
    assert "## 4. Verified Data Flow & Architecture" in res["prompt_digest"]
    assert "OrderController" in res["prompt_digest"]
    assert res["stats"]["manifests_detected"] >= 2


# ===========================================================================
# 2. DeepWiki Page Synthesis Tests
# ===========================================================================

def test_deepwiki_conditional_page_synthesis(sample_snapshot: SnapshotRecord, sample_repo_model):
    gen = DocumentationPageGenerator(sample_snapshot, sample_repo_model, use_llm=False)
    pages = gen.generate_all_pages()
    page_ids = {p.id for p in pages}

    # Verify core conditional pages are planned and generated
    assert "overview" in page_ids
    assert "core_architecture" in page_ids or "architecture" in page_ids
    assert len(pages) >= 4

    # Check overview page content
    overview = next(p for p in pages if p.id == "overview")
    assert "sample-service" in overview.sections[0].content
    assert overview.status in (PageStatus.VERIFIED, PageStatus.VERIFIED_WITH_SUGGESTIONS)

    # Check architecture page has diagram attached
    arch_page = next((p for p in pages if p.id in ("core_architecture", "architecture")), None)
    assert arch_page is not None
    assert len(arch_page.sections) >= 1
    assert any("Presentation Layer" in s.content or "Architecture" in s.heading for s in arch_page.sections)


def test_deepwiki_honest_insufficient_evidence_when_no_routes(tmp_path: Path):
    empty_dir = tmp_path / "bare_lib"
    empty_dir.mkdir(parents=True, exist_ok=True)
    (empty_dir / "util.py").write_text("def add(a, b): return a + b", encoding="utf-8")
    
    snap = register_snapshot(
        repository_id="bare-lib",
        analysis_run_id="run_bare_lib",
        repo_path=str(empty_dir),
    )
    bare_model = {
        "repo": "bare-lib",
        "repo_path": str(empty_dir),
        "classes": [{"name": "MathUtil", "kind": "module", "file": "util.py", "line_start": 1, "line_end": 5}],
        "relationships": [],
        "endpoints": [],
    }
    gen = DocumentationPageGenerator(snap, bare_model, use_llm=False)
    api_page = gen.generate_page({"id": "api_routes", "title": "API Routes", "purpose": "HTTP handlers"})
    
    assert any("No HTTP routes" in s.content for s in api_page.sections)


# ===========================================================================
# 3. UML Diagram & Mermaid Syntax Tests
# ===========================================================================

def test_mermaid_sanitizer_and_validator():
    bad_id = "123_invalid-name/module.ts"
    sanitized = _sanitize_mermaid_id(bad_id)
    assert not sanitized[0].isdigit()
    assert "/" not in sanitized
    assert "." not in sanitized

    label_with_quotes = 'Component "Special" <Type> [Unclosed'
    escaped = _escape_mermaid_label(label_with_quotes)
    assert '"' not in escaped
    assert "<" not in escaped
    assert ">" not in escaped
    assert "[" not in escaped

    # Validator balances delimiters
    unbalanced = "graph TD\n    A[Unclosed bracket"
    valid_syntax = validate_mermaid_syntax(unbalanced)
    assert valid_syntax.startswith("graph TD")
    assert valid_syntax.count("[") == valid_syntax.count("]")


def test_diagram_generator_deterministic_mermaid(sample_snapshot: SnapshotRecord, sample_repo_model):
    gen = DiagramGenerator(sample_snapshot, sample_repo_model)
    diagrams = gen.generate_all()

    assert DiagramType.DEPENDENCY.value in diagrams
    assert DiagramType.ARCHITECTURE.value in diagrams
    assert DiagramType.CALL_GRAPH.value in diagrams
    assert DiagramType.DATA_FLOW.value in diagrams
    assert DiagramType.SEQUENCE.value in diagrams

    arch_diag = diagrams[DiagramType.ARCHITECTURE.value]
    assert "graph TD" in arch_diag.mermaid_source
    assert "Layer1" in arch_diag.mermaid_source or "Layer" in arch_diag.mermaid_source
    assert len(arch_diag.nodes) >= 3
    assert arch_diag.validate_invariants().valid is True


def test_diagram_ai_annotation_does_not_mutate_topology(sample_snapshot: SnapshotRecord, sample_repo_model):
    gen = DiagramGenerator(sample_snapshot, sample_repo_model)
    diag = gen.generate_dependency_diagram()
    initial_node_count = len(diag.nodes)
    initial_edge_count = len(diag.edges)

    with patch("devlensx.llm.provider.get_llm_provider") as mock_get_llm:
        mock_provider = MagicMock()
        mock_provider.capabilities.return_value = {"offline": False}
        mock_provider.generate.return_value = "Verified downstream coupling from OrderController to service tier."
        mock_get_llm.return_value = mock_provider

        gen._annotate_with_ai(diag)
        # Description is enriched
        assert "Verified downstream coupling" in diag.description
        # Topology is strictly unchanged
        assert len(diag.nodes) == initial_node_count
        assert len(diag.edges) == initial_edge_count


# ===========================================================================
# 4. AI Provider Hardening Tests (Google AI Studio & OpenAI)
# ===========================================================================

def test_gemini_loads_google_ai_studio_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSy_GoogleStudioKey_Test12345")
    p = GeminiProvider()
    assert p.api_key == "AIzaSy_GoogleStudioKey_Test12345"
    assert p.health()["ok"] is True
    assert p.model() in ("gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash")


def test_openai_loads_key_and_custom_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-testkey123456789")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    p = OpenAIProvider()
    assert p.api_key == "sk-proj-testkey123456789"
    assert p.model() == "gpt-4o-mini"
    assert p.health()["ok"] is True


def test_safe_error_redacts_credentials():
    err_with_key = Exception("HTTP 400 at https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSy_Secret_Key_Val")
    redacted = _safe_error(err_with_key)
    assert "AIzaSy_Secret_Key_Val" not in redacted
    assert "***REDACTED***" in redacted

    err_with_bearer = Exception("Unauthorized: Bearer sk-proj-1234567890abcdef")
    redacted_bearer = _safe_error(err_with_bearer)
    assert "sk-proj-1234567890abcdef" not in redacted_bearer
    assert "Bearer ***REDACTED***" in redacted_bearer
