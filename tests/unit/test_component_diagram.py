"""
DevLensX Unit Test Suite: D6.3 Component / Module Graph
Verifies module/package hierarchy and containment relationships using domain cluster structure.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.diagrams.generator import DiagramGenerator
from devlensx.diagrams.models import DiagramType


def test_component_diagram():
    print("Executing Unit Test: D6.3 Component / Module Graph...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_component_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    gen = DiagramGenerator(snapshot, model)
    diagram = gen.generate_component_diagram()

    assert diagram.type == DiagramType.COMPONENT
    assert len(diagram.nodes) > 0
    assert "graph TD" in diagram.mermaid_source
    assert "subgraph" in diagram.mermaid_source

    # Check node metadata and validation
    val = diagram.validate_invariants()
    assert val.valid is True
    assert val.verified_nodes > 0

    print(f"  🟢 Component Diagram Verified: {len(diagram.nodes)} nodes across domain packages.")
    print("Unit Test Component Diagram Complete: 100% Passed\n")


if __name__ == "__main__":
    test_component_diagram()
