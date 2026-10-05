"""
DevLensX Unit Test Suite: D6.7 Sequence Diagram
Verifies that inferred sequence transitions carry explicit AI_SUGGESTION tags.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.diagrams.generator import DiagramGenerator
from devlensx.diagrams.models import DiagramType


def test_sequence_diagram():
    print("Executing Unit Test: D6.7 Sequence Diagram...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_sequence_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    gen = DiagramGenerator(snapshot, model)
    diagram = gen.generate_sequence_diagram()

    assert diagram.type == DiagramType.SEQUENCE
    assert diagram.verdict == "AI_SUGGESTION"
    assert "sequenceDiagram" in diagram.mermaid_source

    # Check that inferred transitions carry AI_SUGGESTION verdict
    for edge in diagram.edges:
        assert edge.verdict == "AI_SUGGESTION"

    val = diagram.validate_invariants()
    assert val.valid is True
    assert val.inferred_edges > 0

    print("  🟢 Sequence Diagram Verified: Inferred transitions explicitly tagged AI_SUGGESTION.")
    print("Unit Test Sequence Diagram Complete: 100% Passed\n")


if __name__ == "__main__":
    test_sequence_diagram()
