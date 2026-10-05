"""
DevLensX Unit Test Suite: Universal Repository Model (URM)
Verifies language-agnostic Symbol, Relationship, and Endpoint schemas.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.urm.models import (
    UniversalRepositoryModel,
    URMSymbol,
    URMRelationship,
    URMEndpoint,
    SymbolKind,
    RelationshipType,
    SourceLocation
)


def test_urm_model():
    print("Executing Unit Test: Universal Repository Model (URM) Schema...")

    sym_java = URMSymbol(
        id="java_1",
        name="OwnerController",
        qualified_name="org.samples.petclinic.owner.OwnerController",
        kind=SymbolKind.CLASS,
        language="java",
        location=SourceLocation(file_path="OwnerController.java", start_line=1, end_line=50),
        stereotype="Controller"
    )

    sym_py = URMSymbol(
        id="py_1",
        name="user_router",
        qualified_name="app.routers.user_router",
        kind=SymbolKind.FUNCTION,
        language="python",
        location=SourceLocation(file_path="user_router.py", start_line=1, end_line=30),
        stereotype="Controller"
    )

    rel = URMRelationship(
        source_id=sym_java.id,
        target_id=sym_py.id,
        relationship_type=RelationshipType.CALLS,
        language="polyglot"
    )

    ep = URMEndpoint(
        route="/api/v1/users",
        http_method="GET",
        handler_symbol_id=sym_py.id,
        framework="FastAPI",
        location=SourceLocation(file_path="user_router.py", start_line=1)
    )

    urm = UniversalRepositoryModel(
        repository_id="polyglot_repo",
        name="Polyglot Microservice Workspace",
        root_path="/app",
        primary_language="Polyglot",
        symbols=[sym_java, sym_py],
        relationships=[rel],
        endpoints=[ep]
    )

    assert len(urm.symbols) == 2
    assert len(urm.relationships) == 1
    assert len(urm.endpoints) == 1
    assert urm.symbols[0].kind == SymbolKind.CLASS
    assert urm.symbols[1].language == "python"

    print(f"  🟢 URM Verified: {len(urm.symbols)} Symbols across Java/Python mapped to language-neutral representation.")
    print("Unit Test URM Complete: 100% Passed\n")


if __name__ == "__main__":
    test_urm_model()
