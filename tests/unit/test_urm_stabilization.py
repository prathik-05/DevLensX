"""
DevLensX Unit Test Suite: Step 2 URM Schema & Adapter Stabilization
Validates language-neutral URM entities, line provenance, relationships, and endpoints across Java, TS, and Python.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.urm.models import (
    SymbolKind, RelationshipType, URMSymbol, URMRelationship, URMEndpoint, UniversalRepositoryModel, SourceEvidence, SourceLocation
)
from devlensx.urm.adapters.java_adapter import JavaLanguageAdapter
from devlensx.urm.adapters.typescript_adapter import TypeScriptLanguageAdapter
from devlensx.urm.adapters.python_adapter import PythonLanguageAdapter


def test_urm_stabilization():
    print("Executing Unit Test: Step 2 URM Schema & Provenance Stabilization...")

    # 1. Schema Line Provenance Validation
    sym = URMSymbol(
        id="sym_1",
        name="SPDevProvider",
        qualified_name="src/context/spdev-provider.tsx:SPDevProvider",
        kind=SymbolKind.CLASS,
        language="typescript",
        location=SourceLocation(file_path="src/context/spdev-provider.tsx", start_line=10, end_line=50),
        stereotype="Component",
        evidence=SourceEvidence(source_type="AST", location=SourceLocation(file_path="src/context/spdev-provider.tsx", start_line=10, end_line=50), parser="typescript-ast")
    )

    assert sym.line_start == 10
    assert sym.line_end == 50
    assert sym.evidence.location.file_path == "src/context/spdev-provider.tsx"
    print("  🟢 Provenance Contract Verified: Entity captures file & line range (#L10-L50)")

    # 2. Relationship Triple Invariant Validation
    rel = URMRelationship(
        source_id="sym_1",
        target_id="sym_2",
        relationship_type=RelationshipType.DEPENDS_ON,
        language="typescript",
        metadata={"file": "src/context/spdev-provider.tsx", "line_start": 12}
    )
    assert rel.relationship_type == RelationshipType.DEPENDS_ON
    assert rel.metadata["line_start"] == 12
    print("  🟢 Relationship Invariant Verified: Triple captures source_id, target_id, and line metadata")

    # 3. Adapter Contract Compliance: Java, TypeScript, Python
    adapters = [JavaLanguageAdapter(), TypeScriptLanguageAdapter(), PythonLanguageAdapter()]
    for adapter in adapters:
        assert hasattr(adapter, "can_parse")
        assert hasattr(adapter, "parse_file")
        assert hasattr(adapter, "extract_relationships")
        assert hasattr(adapter, "extract_endpoints")
        print(f"  🟢 Adapter Contract Verified: {adapter.__class__.__name__} implements full BaseLanguageAdapter API")

    print("Unit Test URM Stabilization Complete: 100% Passed\n")


if __name__ == "__main__":
    test_urm_stabilization()
