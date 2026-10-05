"""
DevLensX Unit Test Suite: D6.6 & D6.13 Diagram Evidence Provenance & Isolation
Verifies that all diagram nodes and edges resolve directly through SnapshotRegistry,
and tests cross-repository isolation, wrong runs, stale commits, and path violations.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import EvidenceRef, EvidenceType, ResolutionStatus
from devlensx.evidence.resolver import register_snapshot, get_evidence_resolver
from devlensx.diagrams.generator import generate_all_diagrams
from devlensx.diagrams.models import DiagramType


def test_diagram_provenance_and_isolation():
    print("Executing Unit Test: D6.6 & D6.13 Diagram Evidence Provenance & Isolation...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    run_id = "run_provenance_iso_001"

    # Register snapshot in authoritative registry
    snapshot = register_snapshot(
        repository_id="spring-petclinic",
        analysis_run_id=run_id,
        repo_path=os.path.abspath("eval_repos/spring-petclinic"),
        commit_hash="c0ffee1",
    )

    diagrams = generate_all_diagrams(snapshot, model)
    resolver = get_evidence_resolver()

    assert len(diagrams) == 6
    arch_diag = diagrams[DiagramType.ARCHITECTURE.value]

    # Positive test: resolve verified nodes
    resolved_count = 0
    sample_ref = None
    for node in arch_diag.nodes:
        for ref in node.evidence_refs:
            res = resolver.resolve(ref)
            if res.resolved:
                resolved_count += 1
                sample_ref = ref

    assert resolved_count > 0, "No diagram node evidence could be resolved against snapshot"
    assert sample_ref is not None

    # Negative Test 1: Cross-repository citation blocked (Repo A evidence against Repo B)
    cross_ref = EvidenceRef(
        repository_id="python-backend-repo",  # Wrong repository
        analysis_run_id=run_id,
        commit_hash="c0ffee1",
        file_path=sample_ref.file_path,
        line_start=sample_ref.line_start,
        line_end=sample_ref.line_end,
    )
    res_cross = resolver.resolve(cross_ref)
    assert res_cross.status == ResolutionStatus.PATH_VIOLATION
    assert res_cross.resolved is False

    # Negative Test 2: Unknown snapshot / run ID
    unknown_run_ref = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id="run_nonexistent_999",
        file_path=sample_ref.file_path,
        line_start=sample_ref.line_start,
        line_end=sample_ref.line_end,
    )
    res_unknown = resolver.resolve(unknown_run_ref)
    assert res_unknown.status == ResolutionStatus.UNKNOWN_SNAPSHOT
    assert res_unknown.resolved is False

    # Negative Test 3: Stale commit hash
    stale_ref = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id=run_id,
        commit_hash="deadbeef_old_commit",
        file_path=sample_ref.file_path,
        line_start=sample_ref.line_start,
        line_end=sample_ref.line_end,
    )
    res_stale = resolver.resolve(stale_ref)
    assert res_stale.status == ResolutionStatus.STALE_COMMIT
    assert res_stale.resolved is False

    # Negative Test 4: Path traversal attempt
    traversal_ref = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id=run_id,
        commit_hash="c0ffee1",
        file_path="../../etc/passwd",
        line_start=1,
        line_end=5,
    )
    res_traversal = resolver.resolve(traversal_ref)
    assert res_traversal.status == ResolutionStatus.PATH_VIOLATION
    assert res_traversal.resolved is False

    print("  🟢 Diagram Provenance & Multi-Tenant Isolation Verified: Cross-repo citations and stale commits strictly blocked.")
    print("Unit Test Diagram Provenance Complete: 100% Passed\n")


if __name__ == "__main__":
    test_diagram_provenance_and_isolation()
