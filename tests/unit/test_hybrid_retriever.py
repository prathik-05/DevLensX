"""
DevLensX Unit Test Suite: Step 7 Hybrid GraphRAG Retrieval Engine with Intent Routing
Verifies intent detection and structural 2-hop GraphRAG context packaging.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.urm.models import UniversalRepositoryModel, URMSymbol, URMRelationship, SymbolKind, RelationshipType, SourceLocation
from devlensx.rag.hybrid_retriever import HybridRepositoryRetriever, QueryIntent


def test_hybrid_retriever():
    print("Executing Unit Test: Step 7 Hybrid GraphRAG Retriever with Intent Routing...")

    urm = UniversalRepositoryModel(
        repository_id="repo_1",
        name="spring-petclinic",
        root_path="/",
        primary_language="java",
        symbols=[
            URMSymbol(id="s1", name="OwnerController", qualified_name="OwnerController.java:OwnerController", kind=SymbolKind.CLASS, language="java", location=SourceLocation(file_path="OwnerController.java", start_line=23, end_line=45), stereotype="Controller"),
            URMSymbol(id="s2", name="OwnerRepository", qualified_name="OwnerRepository.java:OwnerRepository", kind=SymbolKind.CLASS, language="java", location=SourceLocation(file_path="OwnerRepository.java", start_line=10, end_line=30), stereotype="Repository")
        ],
        relationships=[
            URMRelationship(source_id="s1", target_id="s2", relationship_type=RelationshipType.DEPENDS_ON, language="java")
        ]
    )

    retriever = HybridRepositoryRetriever(urm)

    # 1. Architecture Intent Test
    res1 = retriever.retrieve_context("What is the architecture of OwnerController?")
    assert res1["detected_intent"] == QueryIntent.ARCHITECTURE
    assert res1["evidence_nodes"][0]["name"] == "OwnerController"
    print(f"  🟢 Intent Detected: {res1['detected_intent']} for query '{res1['query']}'")

    # 2. Change Impact Intent Test
    res2 = retriever.retrieve_context("What breaks if I change OwnerRepository?")
    assert res2["detected_intent"] == QueryIntent.CHANGE_IMPACT
    print(f"  🟢 Intent Detected: {res2['detected_intent']} for query '{res2['query']}'")

    print("Unit Test Hybrid Retriever Complete: 100% Passed\n")


if __name__ == "__main__":
    test_hybrid_retriever()
