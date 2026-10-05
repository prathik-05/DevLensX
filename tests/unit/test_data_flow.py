"""
DevLensX Unit Test Suite: D6.6 Data Flow Pipeline
Verifies honest representation of complete and incomplete data flow chains.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.diagrams.generator import DiagramGenerator
from devlensx.diagrams.models import DiagramType


def test_data_flow_diagram():
    print("Executing Unit Test: D6.6 Data Flow Pipeline...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_dataflow_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    gen = DiagramGenerator(snapshot, model)
    diagram = gen.generate_data_flow_diagram()

    assert diagram.type == DiagramType.DATA_FLOW
    assert len(diagram.nodes) > 0
    assert "graph LR" in diagram.mermaid_source

    val = diagram.validate_invariants()
    assert val.valid is True

    print(f"  🟢 Data Flow Diagram Verified: {len(diagram.nodes)} pipeline nodes with honest link bounds.")
    print("Unit Test Data Flow Complete: 100% Passed\n")


if __name__ == "__main__":
    test_data_flow_diagram()
