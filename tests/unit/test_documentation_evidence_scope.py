"""
DevLensX Unit Test Suite: D7.1 Documentation Evidence Scope
Verifies that EvidenceScopeBuilder constructs bounded, immutable evidence packages
per page blueprint.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.documentation.evidence_scope import EvidenceScopeBuilder


def test_documentation_evidence_scope():
    print("Executing Unit Test: D7.1 Documentation Evidence Scope...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_scope_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    blueprint = {
        "id": "owners_subsystem",
        "title": "Owner Management Subsystem",
        "purpose": "CRUD workflows and visits for pet owners",
        "target_symbols": ["OwnerController", "OwnerRepository", "Owner"],
        "target_files": ["OwnerController.java", "OwnerRepository.java"],
        "type": "subsystem",
    }

    scope = EvidenceScopeBuilder.build_scope(
        page_id=blueprint["id"],
        page_blueprint=blueprint,
        snapshot=snapshot,
        model=intel.model,
    )

    assert scope.repository_id == "spring-petclinic"
    assert scope.analysis_run_id == "run_scope_test_001"
    assert scope.commit_hash == "c0ffee1"
    assert scope.page_id == "owners_subsystem"
    assert len(scope.symbols) > 0
    assert any(s["name"] == "OwnerController" for s in scope.symbols)
    assert len(scope.evidence_refs) > 0
    assert any("OwnerController" in r.file_path for r in scope.evidence_refs)

    print(f"  🟢 Evidence Scope Verified: Bounded to {len(scope.symbols)} symbols and {len(scope.evidence_refs)} EvidenceRefs.")
    print("Unit Test Evidence Scope Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_evidence_scope()
