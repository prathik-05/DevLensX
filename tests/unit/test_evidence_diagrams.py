"""
DevLensX Unit Test Suite: Step 5 Evidence-Grounded Diagram Generator
Verifies Mermaid diagram generation linking nodes to file line ranges (#L23-45).
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.urm.models import URMSymbol, URMRelationship, SymbolKind, RelationshipType, SourceLocation
from devlensx.understanding.diagram_generator import EvidenceDiagramGenerator


def test_evidence_diagrams():
    print("Executing Unit Test: Step 5 Evidence-Grounded Diagram Generator...")

    symbols = [
        URMSymbol(id="s1", name="OwnerController", qualified_name="OwnerController.java:OwnerController", kind=SymbolKind.CLASS, language="java", location=SourceLocation(file_path="OwnerController.java", start_line=23, end_line=45), stereotype="Controller"),
        URMSymbol(id="s2", name="OwnerRepository", qualified_name="OwnerRepository.java:OwnerRepository", kind=SymbolKind.CLASS, language="java", location=SourceLocation(file_path="OwnerRepository.java", start_line=10, end_line=30), stereotype="Repository")
    ]

    relationships = [
        URMRelationship(source_id="s1", target_id="s2", relationship_type=RelationshipType.DEPENDS_ON, language="java")
    ]

    mermaid_str = EvidenceDiagramGenerator.generate_architecture_diagram(symbols, relationships)

    assert "graph TD" in mermaid_str
    assert "OwnerController (L23-L45)" in mermaid_str
    assert "OwnerRepository (L10-L30)" in mermaid_str
    assert "depends_on" in mermaid_str

    print("  🟢 Evidence Diagram Verified: Nodes include exact line provenance (#L23-L45)")
    print("Unit Test Evidence Diagrams Complete: 100% Passed\n")


if __name__ == "__main__":
    test_evidence_diagrams()
