"""
DevLensX Unit Test Suite: D6.2.1 Dependency Diagram Generator
Verifies generation of DEPENDS_ON relationship diagram from real repository model.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.diagrams.generator import DiagramGenerator
from devlensx.diagrams.models import DiagramType


def test_dependency_diagram():
    print("Executing Unit Test: D6.2.1 Dependency Diagram...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_petclinic_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    gen = DiagramGenerator(snapshot, model)
    diagram = gen.generate_dependency_diagram()

    assert diagram.type == DiagramType.DEPENDENCY
    assert len(diagram.nodes) > 0
    assert len(diagram.edges) > 0
    assert "graph TD" in diagram.mermaid_source

    # Check node provenance
    owner_ctrl = next((n for n in diagram.nodes if n.id == "OwnerController"), None)
    assert owner_ctrl is not None, "OwnerController node missing in dependency diagram"
    assert len(owner_ctrl.evidence_refs) > 0
    assert owner_ctrl.evidence_refs[0].file_path.endswith("OwnerController.java")
    assert owner_ctrl.evidence_refs[0].line_start >= 1

    print(f"  🟢 Dependency Diagram Verified: {len(diagram.nodes)} nodes, {len(diagram.edges)} edges with line provenance.")
    print("Unit Test Dependency Diagram Complete: 100% Passed\n")


if __name__ == "__main__":
    test_dependency_diagram()
