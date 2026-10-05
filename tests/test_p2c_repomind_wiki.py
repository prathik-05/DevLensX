"""
DevLensX Phase P2-C: RepoMind Living Wiki Test Suite
Validates:
1. Multi-Archetype Polyglot Profiling (Java, TypeScript, Python).
2. Non-Java narrative isolation (zero Spring Boot / Java controller hallucination).
3. Exact AST Line-Level Citations ([file#Lstart-Lend]).
4. Explicit Claim Taxonomy (Observed/Verified vs Inferred/Suggestion).
5. Deterministic Mermaid Diagrams from AST / graph edges.
6. Persistent Wiki Storage & Exact Snapshot Recovery across restarts.
7. Fail-closed Isolation (unknown run_id returns 404, no cross-run leaks).
"""

import os
import sys
import shutil
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from devlensx.evidence.models import SnapshotRecord
from devlensx.core.persistence import SnapshotStorageManager, get_storage_manager
from devlensx.evidence.resolver import get_snapshot_registry, register_snapshot
from devlensx.chat.orchestrator import _model_store, store_model
from devlensx.understanding.profiling.repository_profiler import RepositoryProfiler
from devlensx.wiki import (
    generate_wiki_pages,
    build_and_cache_wiki,
    get_wiki_tree,
    get_wiki_page,
    _wiki_cache,
    WikiPage,
)
from fastapi.testclient import TestClient
from devlensx.api.main import app


@pytest.fixture
def isolated_storage():
    """Temporary storage manager for isolated wiki persistence tests."""
    tmp_dir = tempfile.mkdtemp(prefix="devlensx_p2c_test_")
    mgr = SnapshotStorageManager(base_dir=tmp_dir)
    yield mgr, tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_polyglot_archetype_profiling():
    """1. Validates multi-archetype profiling across Java, TypeScript, and Python."""
    # Java / PetClinic
    petclinic_classes = [
        {"name": "OwnerController", "file": "src/main/java/org/petclinic/OwnerController.java", "stereotype": "Controller"},
        {"name": "OwnerRepository", "file": "src/main/java/org/petclinic/OwnerRepository.java", "stereotype": "Repository"},
    ]
    prof_java = RepositoryProfiler.profile_repository("eval_repos/spring-petclinic", petclinic_classes)
    assert prof_java["primary_language"] == "Java"
    assert prof_java["archetype"] == "WEB_BACKEND"
    assert "Spring Boot" in prof_java["framework"]
    assert prof_java["archetype_status"] == "INFERRED"

    # TypeScript / Portfolio
    ts_classes = [
        {"name": "App", "file": "src/App.tsx", "stereotype": "Component"},
        {"name": "Navbar", "file": "src/components/Navbar.tsx", "stereotype": "Component"},
    ]
    prof_ts = RepositoryProfiler.profile_repository("eval_repos/sp-portfolio", ts_classes)
    assert prof_ts["primary_language"] in ("TypeScript", "JavaScript")
    assert prof_ts["archetype"] == "FRONTEND_UI"
    assert "React" in prof_ts["framework"] or "Next.js" in prof_ts["framework"]

    # Python / Battleship
    py_classes = [
        {"name": "BattleshipGame", "file": "battleship.py", "stereotype": "Class"},
        {"name": "Board", "file": "board.py", "stereotype": "Class"},
    ]
    prof_py = RepositoryProfiler.profile_repository("eval_repos/battleship-python", py_classes)
    assert prof_py["primary_language"] == "Python"
    assert prof_py["archetype"] in ("CLI_ENGINE", "MODULAR_APPLICATION")
    assert "Spring Boot" not in prof_py["framework"]
    assert prof_py["databases"] == ["None Explicitly Declared"]


def test_non_java_narrative_isolation():
    """2. Non-Java repository wiki must never leak Spring Boot or Java controller artifacts."""
    py_model = {
        "repo": "battleship-python",
        "repo_path": "eval_repos/battleship-python",
        "classes": [
            {"name": "BattleshipGame", "file": "battleship.py", "line_start": 10, "line_end": 150, "stereotype": "Class"},
            {"name": "Board", "file": "board.py", "line_start": 5, "line_end": 80, "stereotype": "Class"},
        ],
        "relationships": [
            {"source": "BattleshipGame", "target": "Board", "type": "DEPENDS_ON"}
        ],
        "endpoints": [],
        "repo_summary": {"language": "Python", "framework": "None", "total_classes": 2}
    }

    pages = generate_wiki_pages(py_model, None, [], "run_py_narrative_01", "battleship-python", "commit_py")
    all_content = " ".join(" ".join(s.get("content", "") for s in p.sections) for p in pages)

    banned_spring_terms = [
        "@SpringBootApplication",
        "org.springframework",
        "BindingResult",
        "@Transactional",
        "Autowired",
        "H2 Database",
    ]
    for term in banned_spring_terms:
        assert term not in all_content, f"Banned Spring term '{term}' leaked into Python wiki narrative!"


def test_ast_citations_exact_line_spans():
    """3. All citations must resolve to exact AST line spans [file#Lstart-Lend]."""
    model = {
        "repo": "spring-petclinic",
        "repo_path": "eval_repos/spring-petclinic",
        "classes": [
            {
                "name": "OwnerController",
                "file": "src/main/java/org/petclinic/OwnerController.java",
                "line_start": 42,
                "line_end": 118,
                "stereotype": "Controller",
                "kind": "class",
            },
            {
                "name": "OwnerRepository",
                "file": "src/main/java/org/petclinic/OwnerRepository.java",
                "line_start": 20,
                "line_end": 65,
                "stereotype": "Repository",
                "kind": "interface",
            }
        ],
        "relationships": [
            {"source": "OwnerController", "target": "OwnerRepository", "type": "DEPENDS_ON"}
        ],
        "endpoints": [
            {"method": "GET", "route": "/owners", "handler": "OwnerController.findOwners", "file": "src/main/java/org/petclinic/OwnerController.java"}
        ],
        "repo_summary": {"language": "Java", "framework": "Spring Boot", "total_classes": 2}
    }

    pages = generate_wiki_pages(model, None, [], "run_cite_test", "spring-petclinic", "abc123")
    assert pages

    found_citations = 0
    for p in pages:
        for c in p.citations:
            found_citations += 1
            assert c.get("nodeId"), "Citation missing nodeId"
            assert c.get("file"), "Citation missing file"
            assert c.get("line_start") is not None, "Citation missing line_start"
            assert c.get("line_end") is not None, "Citation missing line_end"
            assert c.get("citation_ref"), "Citation missing citation_ref"
            assert c["citation_ref"].startswith("[") and c["citation_ref"].endswith("]")
            assert "#L" in c["citation_ref"]
            assert str(c["line_start"]) in c["citation_ref"]

    assert found_citations >= 2, f"Expected at least 2 AST citations, found {found_citations}"


def test_explicit_claim_taxonomy_and_badges():
    """4. Claims and badges must distinguish Observed/Verified from Inferred/Suggestion."""
    model = {
        "repo": "test-taxonomy",
        "repo_path": "eval_repos/spring-petclinic",
        "classes": [
            {"name": "OwnerController", "file": "OwnerController.java", "line_start": 1, "line_end": 50, "stereotype": "Controller", "kind": "class"}
        ],
        "relationships": [],
        "endpoints": [],
        "repo_summary": {"language": "Java", "framework": "Spring Boot", "total_classes": 1}
    }

    pages = generate_wiki_pages(model, None, [], "run_tax_test", "test-taxonomy", "abc123")
    overview = next(p for p in pages if p.id == "overview")

    # Inferred archetype section (explicitly unverified / inferred per trust contract)
    archetype_sec = next((s for s in overview.sections if s["heading"] == "Architectural Archetype"), None)
    if archetype_sec:
        assert archetype_sec.get("verdict") == "Unverified", f"Archetype should be Unverified/Inferred, got {archetype_sec.get('verdict')}"
        assert archetype_sec.get("inference") == "INFERRED_SUGGESTION"
        arch_badge = next((b for b in overview.badges if b["section"] == "Architectural Archetype"), None)
        assert arch_badge and arch_badge["verdict"] == "Unverified"

    # AST-grounded repository identity section must be Verified
    repo_id_sec = next((s for s in overview.sections if "What This Project Does" in s["heading"] or "Repository Identity" in s["heading"]), None)
    assert repo_id_sec is not None
    assert repo_id_sec.get("verdict") == "Verified"


def test_deterministic_mermaid_topology():
    """5. Mermaid diagrams must be deterministic from AST edges (no LLM topology)."""
    model = {
        "repo": "test-mermaid",
        "classes": [
            {"name": "Alpha", "file": "Alpha.java", "line_start": 1, "line_end": 10, "stereotype": "Controller", "kind": "class"},
            {"name": "Beta", "file": "Beta.java", "line_start": 1, "line_end": 10, "stereotype": "Service", "kind": "class"},
        ],
        "relationships": [
            {"source": "Alpha", "target": "Beta", "type": "DEPENDS_ON"}
        ],
        "endpoints": [],
        "repo_summary": {"language": "Java", "framework": "Spring Boot", "total_classes": 2}
    }

    pages_run1 = generate_wiki_pages(model, None, [], "run_mm_1", "test-mermaid", "c1")
    pages_run2 = generate_wiki_pages(model, None, [], "run_mm_2", "test-mermaid", "c1")

    arch1 = next(p for p in pages_run1 if p.id == "architecture")
    arch2 = next(p for p in pages_run2 if p.id == "architecture")

    assert arch1.mermaid, "Missing architecture mermaid diagram"
    assert arch1.mermaid == arch2.mermaid, "Mermaid diagram is not 100% deterministic across runs"
    assert "Alpha" in arch1.mermaid and "Beta" in arch1.mermaid


def test_wiki_persistence_and_exact_recovery():
    """6. Validates atomic save_wiki, process restart survival, and exact snapshot recovery."""
    run_id = "run_p2c_persist_exact"
    repo_id = "spring-petclinic"
    commit = "commit_exact_p2c"

    snap = SnapshotRecord(
        repository_id=repo_id,
        analysis_run_id=run_id,
        repo_path="eval_repos/spring-petclinic",
        commit_hash=commit
    )
    model = {
        "repo": repo_id,
        "classes": [
            {"name": "VetController", "file": "VetController.java", "line_start": 10, "line_end": 80, "stereotype": "Controller", "kind": "class"},
            {"name": "VetRepository", "file": "VetRepository.java", "line_start": 5, "line_end": 40, "stereotype": "Repository", "kind": "interface"},
        ],
        "relationships": [
            {"source": "VetController", "target": "VetRepository", "type": "DEPENDS_ON"}
        ],
        "endpoints": [
            {"method": "GET", "route": "/vets", "handler": "VetController.showVetList", "file": "VetController.java"}
        ],
        "repo_summary": {"language": "Java", "framework": "Spring Boot", "total_classes": 2}
    }

    # 1. Register snapshot and persist model
    register_snapshot(snap.repository_id, snap.analysis_run_id, snap.repo_path, snap.commit_hash)
    store_model(run_id, model)
    get_storage_manager().save_snapshot(snap, model)

    # 2. Build and cache wiki (persists wiki.json to disk atomically)
    pages = build_and_cache_wiki(model, None, [], run_id, repo_id, commit)
    assert len(pages) >= 4

    # 3. Simulate process restart: completely clear in-memory caches
    _wiki_cache.invalidate_all()
    _model_store.pop(run_id, None)

    # 4. Verify exact recovery via GET /api/wiki/{analysis_id}
    client = TestClient(app)
    resp = client.get(f"/api/wiki/{run_id}")
    assert resp.status_code == 200, f"Failed exact recovery: {resp.text}"
    tree_data = resp.json()
    assert tree_data["analysis_id"] == run_id
    assert tree_data["repository_id"] == repo_id
    assert tree_data["count"] >= 4

    # 5. Verify individual page retrieval after restart
    page_resp = client.get(f"/api/wiki/{run_id}/page/overview")
    assert page_resp.status_code == 200
    page_data = page_resp.json()
    assert page_data["id"] == "overview"
    assert len(page_data.get("sections", [])) > 0
    assert len(page_data.get("citations", [])) > 0


def test_fail_closed_snapshot_isolation():
    """7. Strict fail-closed isolation: unknown snapshots must return 404, no cross-run leaks."""
    client = TestClient(app)

    # Unknown analysis_id must return 404
    resp_unknown_tree = client.get("/api/wiki/run_unknown_nonexistent_xyz")
    assert resp_unknown_tree.status_code == 404
    assert "not found" in resp_unknown_tree.json()["detail"].lower()

    resp_unknown_page = client.get("/api/wiki/run_unknown_nonexistent_xyz/page/overview")
    assert resp_unknown_page.status_code == 404

    # Run A vs Run B isolation
    run_a = "run_p2c_iso_A"
    run_b = "run_p2c_iso_B"

    snap_a = SnapshotRecord("petclinic", run_a, "eval_repos/spring-petclinic", "commit_a")
    model_a = {
        "repo": "petclinic",
        "classes": [{"name": "OwnerController", "file": "OwnerController.java", "line_start": 1, "line_end": 20, "stereotype": "Controller", "kind": "class"}],
        "relationships": [],
        "endpoints": [],
        "repo_summary": {"language": "Java", "framework": "Spring Boot", "total_classes": 1}
    }

    snap_b = SnapshotRecord("battleship", run_b, "eval_repos/battleship-python", "commit_b")
    model_b = {
        "repo": "battleship",
        "classes": [{"name": "Board", "file": "board.py", "line_start": 1, "line_end": 20, "stereotype": "Class", "kind": "class"}],
        "relationships": [],
        "endpoints": [],
        "repo_summary": {"language": "Python", "framework": "None", "total_classes": 1}
    }

    register_snapshot(snap_a.repository_id, snap_a.analysis_run_id, snap_a.repo_path, snap_a.commit_hash)
    store_model(run_a, model_a)
    build_and_cache_wiki(model_a, None, [], run_a, snap_a.repository_id, snap_a.commit_hash)

    register_snapshot(snap_b.repository_id, snap_b.analysis_run_id, snap_b.repo_path, snap_b.commit_hash)
    store_model(run_b, model_b)
    build_and_cache_wiki(model_b, None, [], run_b, snap_b.repository_id, snap_b.commit_hash)

    # Query A: must contain OwnerController, must NOT contain Board
    page_a = client.get(f"/api/wiki/{run_a}/page/overview").json()
    content_a = " ".join(s.get("content", "") for s in page_a.get("sections", []))
    assert "OwnerController" in content_a or any(c.get("nodeId") == "OwnerController" for c in page_a.get("citations", []))
    assert "Board" not in content_a

    # Query B: must contain Board, must NOT contain OwnerController
    page_b = client.get(f"/api/wiki/{run_b}/page/overview").json()
    content_b = " ".join(s.get("content", "") for s in page_b.get("sections", []))
    assert "Board" in content_b or any(c.get("nodeId") == "Board" for c in page_b.get("citations", []))
    assert "OwnerController" not in content_b
