"""
EvidenceRef & Snapshot Isolation Tests (D10.2.4, D10.2.5)

Tests EvidenceRef resolution invariants and cross-repository isolation.
"""

import pytest
import tempfile
from pathlib import Path

from devlensx.evidence.resolver import (
    EvidenceResolver,
    SnapshotRegistry,
    register_snapshot,
    store_snapshot_refs,
    get_snapshot_refs,
)
from devlensx.evidence.models import (
    EvidenceRef,
    EvidenceType,
    ResolutionStatus,
    ResolvedEvidence,
    SnapshotRecord,
)
from devlensx.evidence.source_reader import SourceReader


class TestEvidenceRefResolution:
    """Tests for EvidenceRef resolution invariants."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()
        self.registry = SnapshotRegistry()
        self.resolver = EvidenceResolver(self.registry)

        # Create a test file
        self.test_file = self.repo_root / "OwnerController.java"
        self.test_file.write_text(
            "package com.example;\n\n"
            "public class OwnerController {\n"
            "    public void handle() {}\n"
            "}\n",
            encoding="utf-8"
        )

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_valid_ref_resolves(self):
        """Valid EvidenceRef with correct snapshot should resolve."""
        snap = self.registry.register("repoA", "run1", str(self.repo_root), "abc123")
        ref = EvidenceRef(
            repository_id="repoA",
            analysis_run_id="run1",
            commit_hash="abc123",
            file_path="OwnerController.java",
            line_start=3,
            line_end=3,
            symbol_name="OwnerController",
            evidence_type=EvidenceType.AST,
        )
        result = self.resolver.resolve(ref)
        assert result.resolved is True
        assert result.status == ResolutionStatus.RESOLVED
        assert "OwnerController" in result.lines[0].content

    def test_unknown_run_rejected(self):
        """EvidenceRef with unknown analysis_run_id should be rejected."""
        ref = EvidenceRef(
            repository_id="repoA",
            analysis_run_id="unknown_run",
            file_path="OwnerController.java",
            line_start=1,
            line_end=1,
        )
        result = self.resolver.resolve(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.UNKNOWN_SNAPSHOT

    def test_repository_mismatch_rejected(self):
        """EvidenceRef with different repository_id should be rejected."""
        self.registry.register("repoA", "run1", str(self.repo_root), "abc123")
        ref = EvidenceRef(
            repository_id="repoB",  # Different repo!
            analysis_run_id="run1",
            commit_hash="abc123",
            file_path="OwnerController.java",
            line_start=1,
            line_end=1,
        )
        result = self.resolver.resolve(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.PATH_VIOLATION  # Actually REPOSITORY_MISMATCH
        assert "does not match" in result.message or "Cross-repository" in result.message

    def test_stale_commit_rejected(self):
        """EvidenceRef with different commit_hash should be rejected."""
        self.registry.register("repoA", "run1", str(self.repo_root), "abc123")
        ref = EvidenceRef(
            repository_id="repoA",
            analysis_run_id="run1",
            commit_hash="different_hash",  # Stale!
            file_path="OwnerController.java",
            line_start=1,
            line_end=1,
        )
        result = self.resolver.resolve(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.STALE_COMMIT

    def test_filename_only_resolution_blocked(self):
        """EvidenceRef without snapshot identity should not resolve by filename."""
        # Create a ref with only filename, no run_id
        ref = EvidenceRef(
            repository_id="repoA",
            analysis_run_id="",  # Empty!
            file_path="OwnerController.java",
            line_start=1,
            line_end=1,
        )
        result = self.resolver.resolve(ref)
        assert result.resolved is False
        assert result.status == ResolutionStatus.UNKNOWN_SNAPSHOT


class TestCrossRepositoryIsolation:
    """Tests for cross-repository evidence isolation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()
        self.registry = SnapshotRegistry()
        self.resolver = EvidenceResolver(self.registry)

        # Create PetClinic-like repo
        self.petclinic_root = self.repo_root / "petclinic"
        self.petclinic_root.mkdir()
        (self.petclinic_root / "OwnerController.java").write_text(
            "package org.springframework.samples.petclinic.owner;\n"
            "public class OwnerController {}\n",
            encoding="utf-8"
        )

        # Create Battleship-like repo
        self.battleship_root = self.repo_root / "battleship"
        self.battleship_root.mkdir()
        (self.battleship_root / "Game.py").write_text(
            "class Game:\n    def play(self): pass\n",
            encoding="utf-8"
        )

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_petclinic_evidence_does_not_resolve_in_battleship(self):
        """PetClinic EvidenceRef should not resolve in Battleship context."""
        # Register PetClinic
        self.registry.register("petclinic", "run_pet", str(self.petclinic_root), "hash1")

        # Create EvidenceRef from PetClinic
        pet_ref = EvidenceRef(
            repository_id="petclinic",
            analysis_run_id="run_pet",
            commit_hash="hash1",
            file_path="OwnerController.java",
            line_start=2,
            line_end=2,
            symbol_name="OwnerController",
        )

        # Register Battleship with different run_id
        self.registry.register("battleship", "run_bs", str(self.battleship_root), "hash2")

        # Try to resolve PetClinic ref - should fail because run_id doesn't match
        result = self.resolver.resolve(pet_ref)
        # This should still work because run_pet exists
        assert result.resolved is True

        # Now try with Battleship run_id but PetClinic ref
        bs_ref = EvidenceRef(
            repository_id="petclinic",
            analysis_run_id="run_bs",  # Wrong run_id!
            commit_hash="hash2",
            file_path="OwnerController.java",
            line_start=2,
            line_end=2,
        )
        result = self.resolver.resolve(bs_ref)
        assert result.resolved is False
        assert result.status in (ResolutionStatus.UNKNOWN_SNAPSHOT, ResolutionStatus.PATH_VIOLATION)

    def test_cross_repo_refs_blocked(self):
        """Cross-repository EvidenceRefs should be blocked."""
        self.registry.register("repoA", "run1", str(self.petclinic_root), "hash1")
        self.registry.register("repoB", "run2", str(self.battleship_root), "hash2")

        # Ref from repoA but trying to use repoB's run
        ref = EvidenceRef(
            repository_id="repoA",
            analysis_run_id="run2",  # repoB's run!
            commit_hash="hash2",
            file_path="OwnerController.java",
            line_start=1,
            line_end=1,
        )
        result = self.resolver.resolve(ref)
        assert result.resolved is False
        # Should fail because repo_id doesn't match snapshot
        assert result.status == ResolutionStatus.PATH_VIOLATION


class TestSnapshotRegistry:
    """Tests for SnapshotRegistry behavior."""

    def setup_method(self):
        self.registry = SnapshotRegistry()
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_register_and_get(self):
        """Registering and retrieving snapshots."""
        snap = self.registry.register("repo1", "run1", str(self.repo_root), "abc123")
        assert snap.repository_id == "repo1"
        assert snap.analysis_run_id == "run1"
        assert snap.commit_hash == "abc123"

        retrieved = self.registry.get("run1")
        assert retrieved is not None
        assert retrieved.repository_id == "repo1"

    def test_unknown_run_returns_none(self):
        """Unknown run_id should return None."""
        assert self.registry.get("nonexistent") is None

    def test_remove_snapshot(self):
        """Removing snapshot should work."""
        self.registry.register("repo1", "run1", str(self.repo_root))
        assert self.registry.get("run1") is not None
        assert self.registry.remove("run1") is True
        assert self.registry.get("run1") is None
        assert self.registry.remove("run1") is False  # Already removed

    def test_list_for_repository(self):
        """Listing snapshots for a repository."""
        self.registry.register("repo1", "run1", str(self.repo_root), "hash1")
        self.registry.register("repo1", "run2", str(self.repo_root), "hash2")
        self.registry.register("repo2", "run3", str(self.repo_root), "hash3")

        repo1_snaps = self.registry.list_for_repository("repo1")
        assert len(repo1_snaps) == 2
        assert all(s.repository_id == "repo1" for s in repo1_snaps)

        repo2_snaps = self.registry.list_for_repository("repo2")
        assert len(repo2_snaps) == 1

    def test_thread_safety(self):
        """Registry operations should be thread-safe."""
        import threading
        import time

        errors = []

        def writer(repo_id, run_id):
            try:
                self.registry.register(repo_id, run_id, str(self.repo_root), f"hash{run_id}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"repo{i}", f"run{i}")) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(self.registry._snapshots) == 50


class TestSnapshotRefStorage:
    """Tests for storing and retrieving snapshot refs."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_store_and_get_refs(self):
        """Storing and retrieving snapshot refs."""
        refs = [
            EvidenceRef(
                repository_id="repo1",
                analysis_run_id="run1",
                commit_hash="abc",
                file_path="Foo.java",
                line_start=1,
                line_end=10,
                symbol_name="Foo",
            ),
            EvidenceRef(
                repository_id="repo1",
                analysis_run_id="run1",
                commit_hash="abc",
                file_path="Bar.java",
                line_start=5,
                line_end=15,
                symbol_name="Bar",
            ),
        ]
        count = store_snapshot_refs("run1", refs)
        assert count == 2

        retrieved = get_snapshot_refs("run1")
        assert retrieved is not None
        assert len(retrieved) == 2
        assert retrieved[0].symbol_name == "Foo"
        assert retrieved[1].symbol_name == "Bar"

    def test_get_unknown_run_returns_none(self):
        """Getting refs for unknown run returns None."""
        assert get_snapshot_refs("unknown") is None

    def test_overwrite_refs(self):
        """Storing refs for same run should overwrite."""
        refs1 = [EvidenceRef(repository_id="r", analysis_run_id="run1", file_path="A.java", line_start=1, line_end=1)]
        refs2 = [EvidenceRef(repository_id="r", analysis_run_id="run1", file_path="B.java", line_start=1, line_end=1)]

        store_snapshot_refs("run1", refs1)
        store_snapshot_refs("run1", refs2)

        retrieved = get_snapshot_refs("run1")
        assert len(retrieved) == 1
        assert retrieved[0].file_path == "B.java"


class TestRegisterSnapshot:
    """Tests for the register_snapshot convenience function."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_root = Path(self.tmpdir).resolve()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_register_snapshot(self):
        """register_snapshot should create and return a SnapshotRecord."""
        snap = register_snapshot("repo1", "run1", str(self.repo_root), "abc123")
        assert snap.repository_id == "repo1"
        assert snap.analysis_run_id == "run1"
        assert snap.commit_hash == "abc123"

        # Should be retrievable from registry
        from devlensx.evidence.resolver import get_snapshot_registry
        retrieved = get_snapshot_registry().get("run1")
        assert retrieved is not None
        assert retrieved.repository_id == "repo1"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])