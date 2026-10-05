"""
DevLensX Integration Test Suite: D7 Deterministic URM Fallback
Verifies that when LLM is unavailable, deterministic synthesizer produces
fully verified DocumentationPages adhering to the exact schema.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.documentation.page_generator import DocumentationPageGenerator


def test_documentation_llm_fallback():
    print("Executing Integration Test: D7 Deterministic LLM Fallback...")

    repo_path = os.path.abspath("eval_repos/spring-petclinic")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    snapshot = register_snapshot(
        repository_id="spring-petclinic",
        analysis_run_id="run_fallback_test_001",
        repo_path=repo_path,
        commit_hash="c0ffee1",
    )

    # Explicitly set llm_client=None to force deterministic fallback
    gen = DocumentationPageGenerator(snapshot, intel.model, llm_client=None)
    pages = gen.generate_all_pages()

    assert len(pages) >= 3
    for p in pages:
        assert p.title
        assert len(p.sections) >= 2
        assert p.status in ("VERIFIED", "VERIFIED_WITH_SUGGESTIONS")
        # Ensure at least one section has citations
        has_citations = any(len(s.evidence_refs) > 0 for s in p.sections)
        assert has_citations, f"Page {p.id} had no evidence citations in fallback mode"

    print(f"  🟢 Deterministic LLM Fallback Verified: Generated {len(pages)} structured, evidence-grounded pages without LLM.")
    print("Integration Test LLM Fallback Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_llm_fallback()
