"""
DevLensX Unit Test Suite: D7.2 Evidence Context Partitioner
Verifies 4-channel deterministic evidence + derived semantic context partitioning with trust annotations.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.documentation.evidence_scope import EvidenceScopeBuilder
from devlensx.documentation.evidence_retriever import EvidenceRetriever


def test_documentation_retriever():
    print("Executing Unit Test: D7.2 Evidence Context Partitioner...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_retriever_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    blueprint = {
        "id": "core_architecture",
        "title": "Core Architecture",
        "type": "architecture",
        "target_symbols": ["OwnerController", "ClinicService"],
    }

    scope = EvidenceScopeBuilder.build_scope(
        page_id=blueprint["id"],
        page_blueprint=blueprint,
        snapshot=snapshot,
        model=intel.model,
    )

    context = EvidenceRetriever.partition_context(scope)
    assert "structural_evidence" in context
    assert "relationship_evidence" in context
    assert "source_citations" in context
    assert "diagram_evidence" in context
    assert "semantic_context" in context

    prompt = EvidenceRetriever.build_prompt_context(scope)
    assert "DETERMINISTIC STRUCTURAL EVIDENCE" in prompt
    assert "DETERMINISTIC GRAPH RELATIONSHIPS" in prompt
    assert "DETERMINISTIC SOURCE CITATIONS" in prompt
    assert "DERIVED SEMANTIC CONTEXT" in prompt

    print("  🟢 Evidence Context Partitioner Verified: Explicit trust hierarchy maintained.")
    print("Unit Test Evidence Context Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_retriever()
