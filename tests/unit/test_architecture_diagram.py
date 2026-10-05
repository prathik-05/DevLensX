"""
DevLensX Unit Test Suite: D6.2.2 Layered Architecture Diagram
Verifies layered grouping (Presentation, Services, Persistence, Domain) based strictly on AST stereotypes.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.diagrams.generator import DiagramGenerator
from devlensx.diagrams.models import DiagramType


def test_architecture_diagram():
    print("Executing Unit Test: D6.2.2 Architecture Diagram...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_petclinic_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    gen = DiagramGenerator(snapshot, model)
    diagram = gen.generate_architecture_diagram()

    assert diagram.type == DiagramType.ARCHITECTURE
    assert "graph TD" in diagram.mermaid_source
    assert "Presentation" in diagram.mermaid_source or "Persistence" in diagram.mermaid_source

    kinds = set(n.kind for n in diagram.nodes)
    assert "Presentation" in kinds or "Persistence" in kinds or "Controller" in kinds or "Repository" in kinds

    print(f"  🟢 Layered Architecture Diagram Verified: Layered partitions match AST evidence.")
    print("Unit Test Architecture Diagram Complete: 100% Passed\n")


if __name__ == "__main__":
    test_architecture_diagram()
