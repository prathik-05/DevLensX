"""
DevLensX Unit Test Suite: D6.1 Canonical Diagram Model & Invariant Contract
Verifies that Diagram, DiagramNode, DiagramEdge preserve strict EvidenceRef provenance,
enforces D6.0 validation contract (VERIFIED requires evidence_refs != []), and serializes deterministically.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.evidence.models import EvidenceRef, EvidenceType
from devlensx.diagrams.models import Diagram, DiagramNode, DiagramEdge, DiagramType


def test_diagram_model_contract():
    print("Executing Unit Test: D6.1 Canonical Diagram Model & Invariant Contract...")

    ref1 = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id="run_test_001",
        file_path="src/main/java/org/samples/petclinic/owner/OwnerController.java",
        line_start=23,
        line_end=110,
        commit_hash="c0ffee1",
        symbol_name="OwnerController",
        evidence_type=EvidenceType.AST,
    )

    ref2 = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id="run_test_001",
        file_path="src/main/java/org/samples/petclinic/owner/OwnerRepository.java",
        line_start=15,
        line_end=40,
        commit_hash="c0ffee1",
        symbol_name="OwnerRepository",
        evidence_type=EvidenceType.AST,
    )

    node1 = DiagramNode(id="OwnerController", label="OwnerController", kind="Controller", verdict="VERIFIED", evidence_refs=[ref1])
    node2 = DiagramNode(id="OwnerRepository", label="OwnerRepository", kind="Repository", verdict="VERIFIED", evidence_refs=[ref2])
    node3 = DiagramNode(id="InferredLayer", label="InferredLayer", kind="Layer", verdict="AI_SUGGESTION", evidence_refs=[])

    edge1 = DiagramEdge(
        source="OwnerController",
        target="OwnerRepository",
        relationship="DEPENDS_ON",
        verdict="VERIFIED",
        evidence_refs=[ref1],
    )

    edge2 = DiagramEdge(
        source="OwnerController",
        target="InferredLayer",
        relationship="INFERRED_FLOW",
        verdict="AI_SUGGESTION",
        evidence_refs=[],
    )

    diagram = Diagram(
        id="diag_001",
        type=DiagramType.ARCHITECTURE,
        title="Test Architecture Diagram",
        repository_id="spring-petclinic",
        analysis_run_id="run_test_001",
        commit_hash="c0ffee1",
        nodes=[node1, node2, node3],
        edges=[edge1, edge2],
        mermaid_source="graph TD\n  OwnerController --> OwnerRepository",
        verdict="VERIFIED",
    )

    d_dict = diagram.to_dict()
    assert d_dict["id"] == "diag_001"
    assert d_dict["type"] == "ARCHITECTURE"
    assert len(d_dict["nodes"]) == 3
    assert len(d_dict["edges"]) == 2

    # Invariant: Node contains full EvidenceRef and verdict
    node_ev = d_dict["nodes"][0]["evidence_refs"][0]
    assert node_ev["repository_id"] == "spring-petclinic"
    assert node_ev["analysis_run_id"] == "run_test_001"
    assert node_ev["commit_hash"] == "c0ffee1"
    assert node_ev["file_path"] == "src/main/java/org/samples/petclinic/owner/OwnerController.java"
    assert node_ev["line_start"] == 23
    assert node_ev["line_end"] == 110
    assert d_dict["nodes"][0]["verdict"] == "VERIFIED"
    assert d_dict["nodes"][2]["verdict"] == "AI_SUGGESTION"

    # Invariant: Validation object present and valid
    val = d_dict["validation"]
    assert val["valid"] is True
    assert val["verified_nodes"] == 2
    assert val["inferred_nodes"] == 1
    assert val["unresolved_node_evidence"] == 0

    # Negative Test: Node claiming VERIFIED with no evidence fails invariant
    bad_node = DiagramNode(id="FakeNode", label="FakeNode", kind="Service", verdict="VERIFIED", evidence_refs=[])
    bad_diagram = Diagram(
        id="bad_001",
        type=DiagramType.DEPENDENCY,
        title="Bad Diagram",
        repository_id="spring-petclinic",
        analysis_run_id="run_test_001",
        nodes=[bad_node],
        edges=[],
    )
    bad_val = bad_diagram.validate_invariants()
    assert bad_val.valid is False
    assert bad_val.unresolved_node_evidence == 1
    assert bad_node.verdict == "INSUFFICIENT_EVIDENCE"

    print("  🟢 Canonical Diagram Model & Invariant Contract Verified: VERIFIED requires valid evidence_refs.")
    print("Unit Test Diagram Model Complete: 100% Passed\n")


if __name__ == "__main__":
    test_diagram_model_contract()
