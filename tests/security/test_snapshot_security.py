"""
Snapshot Security & Cross-Repository Isolation Tests (D10.2.5)

Tests that snapshots are properly isolated and cannot leak data across repositories.
"""

import pytest
import tempfile
from pathlib import Path

from devlensx.evidence.resolver import EvidenceResolver, SnapshotRegistry, register_snapshot
from devlensx.evidence.models import (
    EvidenceRef,
    EvidenceType,
    ResolutionStatus,
    SnapshotRecord,
)
from devlensx.workspace.session import WorkspaceSessionRegistry, get_workspace_registry
from devlensx.workspace.orchestrator import UnifiedWorkspaceOrchestrator
from devlensx.workspace.context import WorkspaceContext
from devlensx.impact.analyzer import ImpactAnalyzer
from devlensx.build.planner import BuildPlanner
from devlensx.debug.stacktrace import StackTraceParser
from devlensx.review.review_engine import ReviewEngine
from devlensx.evidence.resolver import get_snapshot_registry


class TestSnapshotIsolation:
    """Tests that snapshots maintain strict isolation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_root = Path(self.tmpdir).resolve()

        # Create two separate repositories
        self.repo_a = self.base_root / "repo_a"
        self.repo_a.mkdir()
        (self.repo_a / "OwnerController.java").write_text(
            "package com.example.a;\npublic class OwnerController {}\n",
            encoding="utf-8"
        )
        (self.repo_a / "ServiceA.java").write_text(
            "package com.example.a;\npublic class ServiceA {}\n",
            encoding="utf-8"
        )

        self.repo_b = self.base_root / "repo_b"
        self.repo_b.mkdir()
        (self.repo_b / "Game.py").write_text(
            "class Game:\n    def play(self): pass\n",
            encoding="utf-8"
        )
        (self.repo_b / "Player.py").write_text(
            "class Player:\n    def move(self): pass\n",
            encoding="utf-8"
        )

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_separate_snapshots_isolated(self):
        """Two separate snapshots should not see each other's data."""
        # Register repo A
        snap_a = register_snapshot("repo_a", "run_a", str(self.repo_a), "hash_a")
        # Register repo B
        snap_b = register_snapshot("repo_b", "run_b", str(self.repo_b), "hash_b")

        assert snap_a.repository_id == "repo_a"
        assert snap_b.repository_id == "repo_b"
        assert snap_a.analysis_run_id != snap_b.analysis_run_id

        # Evidence from A should not resolve in B's context
        ref_a = EvidenceRef(
            repository_id="repo_a",
            analysis_run_id="run_a",
            commit_hash="hash_a",
            file_path="OwnerController.java",
            line_start=2,
            line_end=2,
        )

        # Resolver with A's registry
        resolver_a = EvidenceResolver()
        # Resolver with B's registry (different instance)
        registry_b = SnapshotRegistry()
        registry_b.register("repo_b", "run_b", str(self.repo_b), "hash_b")
        resolver_b = EvidenceResolver(registry_b)

        # ref_a should resolve with resolver_a
        result_a = resolver_a.resolve(ref_a)
        assert result_a.resolved is True

        # ref_a should NOT resolve with resolver_b (different registry)
        result_b = resolver_b.resolve(ref_a)
        assert result_b.resolved is False
        assert result_b.status == ResolutionStatus.UNKNOWN_SNAPSHOT


class TestWorkspaceSessionIsolation:
    """Tests for WorkspaceSession isolation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_root = Path(self.tmpdir).resolve()

        self.repo_a = self.base_root / "repo_a"
        self.repo_a.mkdir()
        (self.repo_a / "OwnerController.java").write_text(
            "package com.example.a;\npublic class OwnerController {}\n",
            encoding="utf-8"
        )

        self.repo_b = self.base_root / "repo_b"
        self.repo_b.mkdir()
        (self.repo_b / "Game.py").write_text(
            "class Game:\n    def play(self): pass\n",
            encoding="utf-8"
        )

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_workspace_sessions_isolated(self):
        """Workspace sessions should be isolated per analysis_run_id."""
        registry = WorkspaceSessionRegistry()

        # Create session for repo A
        session_a = registry.create_or_get("run_a")
        session_a.repository_id = "repo_a"
        session_a.analysis_run_id = "run_a"
        session_a.commit_hash = "hash_a"

        # Create session for repo B
        session_b = registry.create_or_get("run_b")
        session_b.repository_id = "repo_b"
        session_b.analysis_run_id = "run_b"
        session_b.commit_hash = "hash_b"

        # Sessions should be separate
        assert session_a.analysis_run_id != session_b.analysis_run_id
        assert session_a.repository_id != session_b.repository_id

        # Getting session by run_id should return correct one
        retrieved_a = registry.get("run_a")
        assert retrieved_a.repository_id == "repo_a"

        retrieved_b = registry.get("run_b")
        assert retrieved_b.repository_id == "repo_b"

    def test_workspace_context_isolation(self):
        """WorkspaceContext should maintain snapshot identity."""
        ctx_a = WorkspaceContext(
            repository_id="repo_a",
            analysis_run_id="run_a",
            commit_hash="hash_a",
        )
        ctx_b = WorkspaceContext(
            repository_id="repo_b",
            analysis_run_id="run_b",
            commit_hash="hash_b",
        )

        # Contexts should carry their snapshot identity
        assert ctx_a.repository_id == "repo_a"
        assert ctx_b.repository_id == "repo_b"
        assert ctx_a.analysis_run_id != ctx_b.analysis_run_id


class TestImpactAnalyzerIsolation:
    """Tests for ImpactAnalyzer snapshot isolation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_root = Path(self.tmpdir).resolve()

        self.repo_a = self.base_root / "repo_a"
        self.repo_a.mkdir()
        (self.repo_a / "OwnerController.java").write_text(
            "package com.example.a;\npublic class OwnerController {}\n",
            encoding="utf-8"
        )
        (self.repo_a / "ServiceA.java").write_text(
            "package com.example.a;\npublic class ServiceA {}\n",
            encoding="utf-8"
        )

        self.repo_b = self.base_root / "repo_b"
        self.repo_b.mkdir()
        (self.repo_b / "Game.py").write_text(
            "class Game:\n    def play(self): pass\n",
            encoding="utf-8"
        )

        # Register snapshots
        from devlensx.evidence.resolver import get_snapshot_registry
        registry = get_snapshot_registry()
        registry.register("repo_a", "run_a", str(self.repo_a), "hash_a")
        registry.register("repo_b", "run_b", str(self.repo_b), "hash_b")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_impact_isolated_by_run_id(self):
        """Impact analysis should only see symbols from its own run."""
        from devlensx.chat.orchestrator import _model_store

        # Per-run model for run_a (P1-C: no global_state fallback)
        _model_store["run_a"] = {
            "repo": "repo_a",
            "classes": [
                {"name": "OwnerController", "stereotype": "Controller", "file": "OwnerController.java"},
                {"name": "ServiceA", "stereotype": "Service", "file": "ServiceA.java"},
            ],
        }
        try:
            # Run impact for run_a
            impact = ImpactAnalyzer.analyze("OwnerController", "run_a")
            assert impact.repository_id == "repo_a"
            assert impact.analysis_run_id == "run_a"

            # Verify symbols are from repo_a only
            symbols = [d["symbol"] for d in impact.direct + impact.downstream]
            assert all("Controller" in s or "Service" in s for s in symbols)
            assert "Game" not in symbols  # From repo_b
        finally:
            _model_store.pop("run_a", None)


class TestBuildPlannerIsolation:
    """Tests for BuildPlanner snapshot isolation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_root = Path(self.tmpdir).resolve()

        self.repo_a = self.base_root / "repo_a"
        self.repo_a.mkdir()
        (self.repo_a / "OwnerController.java").write_text(
            "package com.example.a;\npublic class OwnerController {}\n",
            encoding="utf-8"
        )

        self.repo_b = self.base_root / "repo_b"
        self.repo_b.mkdir()
        (self.repo_b / "Game.py").write_text(
            "class Game:\n    def play(self): pass\n",
            encoding="utf-8"
        )

        from devlensx.evidence.resolver import get_snapshot_registry
        registry = get_snapshot_registry()
        registry.register("repo_a", "run_a", str(self.repo_a), "hash_a")
        registry.register("repo_b", "run_b", str(self.repo_b), "hash_b")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_build_plan_isolated_by_run_id(self):
        """Build plan should only reference its own repository."""
        from devlensx.chat.orchestrator import _model_store

        _model_store["run_a"] = {
            "repo": "repo_a",
            "classes": [
                {"name": "OwnerController", "stereotype": "Controller", "file": "OwnerController.java"},
            ],
        }

        plan = BuildPlanner.plan("Add feature", "OwnerController", "run_a")
        assert plan.repository_id == "repo_a"
        assert plan.analysis_run_id == "run_a"
        assert plan.commit_hash == "hash_a"

        # Steps should reference repo_a symbols
        for step in plan.steps:
            assert "OwnerController" in step.symbol or "ServiceA" in step.symbol
            assert "Game" not in step.symbol  # Not in repo_a


class TestDebugTraceIsolation:
    """Tests for Debug stack trace snapshot isolation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_root = Path(self.tmpdir).resolve()

        self.repo_a = self.base_root / "repo_a"
        self.repo_a.mkdir()
        (self.repo_a / "OwnerController.java").write_text(
            "package com.example.a;\npublic class OwnerController {\n    public void handle() {}\n}\n",
            encoding="utf-8"
        )

        from devlensx.evidence.resolver import get_snapshot_registry
        registry = get_snapshot_registry()
        registry.register("repo_a", "run_a", str(self.repo_a), "hash_a")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_debug_trace_isolated_by_run_id(self):
        """Debug trace should only resolve locations from its own run."""
        stack_trace = "java.lang.NullPointerException\n    at OwnerController.handle(OwnerController.java:3)"

        result = StackTraceParser.parse(stack_trace, "run_a")
        assert result["repository_id"] == "repo_a"
        assert result["analysis_run_id"] == "run_a"
        assert result["commit_hash"] == "hash_a"

        # Should have verified locations from repo_a
        assert len(result.get("verified_locations", [])) > 0
        assert any("OwnerController" in loc.get("class_name", "") for loc in result.get("verified_locations", []))


class TestReviewEngineIsolation:
    """Tests for ReviewEngine snapshot isolation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_root = Path(self.tmpdir).resolve()

        self.repo_a = self.base_root / "repo_a"
        self.repo_a.mkdir()
        (self.repo_a / "OwnerController.java").write_text(
            "package com.example.a;\npublic class OwnerController {\n    public void handle() {}\n}\n",
            encoding="utf-8"
        )

        from devlensx.evidence.resolver import get_snapshot_registry
        registry = get_snapshot_registry()
        registry.register("repo_a", "run_a", str(self.repo_a), "hash_a")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_review_isolated_by_run_id(self):
        """Review should only analyze symbols from its own run."""
        diff = """diff --git a/OwnerController.java b/OwnerController.java
+++ b/OwnerController.java
@@ -1,3 +1,4 @@
 package com.example.a;
 public class OwnerController {
+    public void newMethod() {}
 }"""

        result = ReviewEngine.review(diff, "run_a")
        assert result["repository_id"] == "repo_a"
        assert result["analysis_run_id"] == "run_a"
        assert result["commit_hash"] == "hash_a"

        # What changed should be from repo_a
        changed = [c["symbol"] for c in result["what_changed"]]
        assert "OwnerController" in changed
        assert "Game" not in changed  # Not in repo_a


class TestWorkspaceOrchestratorSnapshotValidation:
    """Tests for UnifiedWorkspaceOrchestrator snapshot validation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_root = Path(self.tmpdir).resolve()

        self.repo_a = self.base_root / "repo_a"
        self.repo_a.mkdir()
        (self.repo_a / "OwnerController.java").write_text(
            "package com.example.a;\npublic class OwnerController {}\n",
            encoding="utf-8"
        )

        from devlensx.evidence.resolver import get_snapshot_registry
        registry = get_snapshot_registry()
        registry.register("repo_a", "run_a", str(self.repo_a), "hash_a")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_validate_snapshot_unknown_run(self):
        """Unknown run should be rejected."""
        result = UnifiedWorkspaceOrchestrator.validate_snapshot("unknown_run")
        assert result["valid"] is False
        assert result["status"] == "UNKNOWN_RUN"

    def test_validate_snapshot_wrong_repo(self):
        """Wrong repository_id should be rejected."""
        result = UnifiedWorkspaceOrchestrator.validate_snapshot("run_a", repository_id="wrong_repo")
        assert result["valid"] is False
        assert result["status"] == "REPOSITORY_MISMATCH"

    def test_validate_snapshot_stale_commit(self):
        """Stale commit should be rejected."""
        result = UnifiedWorkspaceOrchestrator.validate_snapshot("run_a", commit_hash="different_hash")
        assert result["valid"] is False
        assert result["status"] in ("STALE_COMMIT", "WORKSPACE_STALE")

    def test_validate_snapshot_correct(self):
        """Correct snapshot should validate."""
        result = UnifiedWorkspaceOrchestrator.validate_snapshot("run_a", repository_id="repo_a", commit_hash="hash_a")
        assert result["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])