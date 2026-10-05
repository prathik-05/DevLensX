"""Unit tests for D9.0 Workspace components."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.workspace.context import WorkspaceContext
from devlensx.workspace.session import get_workspace_registry, WorkspaceSessionRegistry
from devlensx.workspace.orchestrator import UnifiedWorkspaceOrchestrator
from devlensx.evidence.models import EvidenceRef
from devlensx.evidence.resolver import get_snapshot_registry, register_snapshot

import os
import sys
import uuid


def test_workspace_context():
    """Test WorkspaceContext creation and serialization."""
    ctx = WorkspaceContext(
        repository_id="test-repo",
        analysis_run_id="run-123",
        commit_hash="abc123",
        page_id="overview",
        section_id="architecture",
        symbol_id="OwnerController",
        diagram_id="diag-1",
        selected_files=["OwnerController.java"],
        current_task="debug",
        mode="DEBUG"
    )
    
    d = ctx.to_dict()
    assert d["repository_id"] == "test-repo"
    assert d["analysis_run_id"] == "run-123"
    assert d["page_id"] == "overview"
    assert d["symbol_id"] == "OwnerController"
    assert d["diagram_id"] == "diag-1"
    assert d["current_task"] == "debug"
    assert d["mode"] == "DEBUG"
    print("WorkspaceContext to_dict OK")

    # Test from_dict
    ctx2 = WorkspaceContext.from_dict(d)
    assert ctx2.repository_id == "test-repo"
    assert ctx2.analysis_run_id == "run-123"
    assert ctx2.symbol_id == "OwnerController"
    print("WorkspaceContext from_dict OK")


def test_workspace_session():
    """Test WorkspaceSession creation and validation."""
    from devlensx.workspace.session import get_workspace_registry, WorkspaceSessionRegistry
    from devlensx.evidence.models import SnapshotRecord
    from devlensx.understanding.model.repository_brain import RepositoryBrain
    from devlensx.evidence.resolver import register_snapshot
    
    # First register a snapshot
    register_snapshot("test-repo", "test_run_123", "/tmp/test", commit_hash="abc123")
    
    reg = get_workspace_registry()
    sess = reg.create_or_get("test_run_123")
    
    assert sess.analysis_run_id == "test_run_123"
    assert sess.repository_id == "test-repo"
    assert sess.commit_hash is not None
    
    # Test context update
    updated = reg.update_context("test_run_123", {"active_page": "overview", "active_symbol": "MyClass"})
    assert updated.active_page == "overview"
    assert updated.active_symbol == "MyClass"
    
    print("WorkspaceSession OK")


def test_snapshot_validation():
    """Test snapshot validation against registry."""
    from devlensx.evidence.resolver import register_snapshot
    register_snapshot("test-repo", "test_run_123", "/tmp/test", commit_hash="abc123")
    
    valid, status = get_workspace_registry().validate("test_run_123", repository_id="test-repo", commit_hash="abc123")
    assert valid
    assert status == "ACTIVE"
    
    # Test with wrong commit
    valid, status = get_workspace_registry().validate("test_run_123", repository_id="test-repo", commit_hash="wrong_hash")
    assert not valid
    assert status == "STALE_COMMIT"
    
    # Test unknown run
    valid, status = get_workspace_registry().validate("unknown_run", repository_id="test-repo")
    assert not valid
    assert status == "UNKNOWN_RUN"
    
    print("Snapshot validation OK")


def test_session_validation():
    from devlensx.workspace.session import get_workspace_registry
    from devlensx.understanding.model.repository_brain import RepositoryBrain
    from devlensx.evidence.resolver import register_snapshot
    
    brain = RepositoryBrain(repo_path="/tmp/test", classes=[{"name": "TestClass", "file": "test.java", "stereotype": "Component", "is_test": False, "methods": [], "endpoints": [], "line_start": 1, "line_end": 10, "file": "test.java", "package": "com.test", "injected_dependencies": []}])
    run_id = brain.analysis_run_id
    
    # Register snapshot for the brain's actual run_id
    from devlensx.evidence.resolver import register_snapshot
    register_snapshot("test-repo", run_id, "/tmp/test", commit_hash="abc123")
    
    reg = get_workspace_registry()
    sess = reg.create_or_get(brain.analysis_run_id)
    
    # Test with wrong run_id (unique id: the shared registry persists across
    # tests in-process, so a fixed id could collide with another suite)
    valid, status = get_workspace_registry().validate("run_unknown_xyzzy_999", repository_id="test-repo", commit_hash=None)
    assert not valid
    assert status == "UNKNOWN_RUN"
    
    # Valid session - use the same repo_id as registered
    valid, status = get_workspace_registry().validate(sess.analysis_run_id, repository_id="test-repo")
    assert valid
    assert status == "ACTIVE"
    
    print("Session validation OK")


def test_orchestrator():
    from devlensx.workspace.orchestrator import UnifiedWorkspaceOrchestrator
    
    # First register a snapshot
    from devlensx.evidence.resolver import register_snapshot
    register_snapshot("test-repo", "run-123", "/tmp/test", commit_hash="abc123")
    
    # Test ensure_session
    result = UnifiedWorkspaceOrchestrator.ensure_session("run-123")
    assert result["valid"] == True
    assert result["status"] == "ACTIVE"
    assert "session" in result
    print("Orchestrator ensure_session OK")


def run_all_tests():
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    
    test_workspace_context()
    test_workspace_session()
    test_snapshot_validation()
    test_session_validation()
    test_orchestrator()
    print("\n✅ All D9.0 unit tests passed!")


if __name__ == "__main__":
    run_all_tests()