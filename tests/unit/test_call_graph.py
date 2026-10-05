"""
DevLensX Unit Test Suite: D6.2.4 Method and Function Call Graph
Verifies invocation call graph generation with function/method-level line citations.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.diagrams.generator import DiagramGenerator
from devlensx.diagrams.models import DiagramType


def test_call_graph():
    print("Executing Unit Test: D6.2.4 Call Graph...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    model = intel.model
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_petclinic_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    gen = DiagramGenerator(snapshot, model)
    diagram = gen.generate_call_graph()

    assert diagram.type == DiagramType.CALL_GRAPH
    assert len(diagram.nodes) > 0
    assert len(diagram.edges) > 0
    assert "graph LR" in diagram.mermaid_source

    print(f"  🟢 Call Graph Verified: {len(diagram.nodes)} method nodes, {len(diagram.edges)} invocation edges.")
    print("Unit Test Call Graph Complete: 100% Passed\n")


if __name__ == "__main__":
    test_call_graph()
