"""
DevLensX Integration Test Suite: D7 Java/Spring PetClinic Wiki Generation
Verifies end-to-end documentation generation and claim verification on real Spring PetClinic repo.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.documentation.page_generator import DocumentationPageGenerator


def test_wiki_petclinic():
    print("Executing Integration Test: D7 Java / Spring PetClinic Wiki Generation...")

    repo_path = os.path.abspath("eval_repos/spring-petclinic")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    snapshot = register_snapshot(
        repository_id="spring-petclinic",
        analysis_run_id="run_petclinic_wiki_001",
        repo_path=repo_path,
        commit_hash="c0ffee1",
    )

    gen = DocumentationPageGenerator(snapshot, intel.model, retriever=intel.retriever)
    pages = gen.generate_all_pages()

    assert len(pages) >= 3, f"Expected at least 3 pages, generated {len(pages)}"
    page_ids = [p.id for p in pages]
    assert any("overview" in p_id or "architecture" in p_id for p_id in page_ids)

    # Verify that pages have verified sections and evidence refs
    total_verified_claims = 0
    total_evidence_refs = 0
    for p in pages:
        assert p.status in ("VERIFIED", "VERIFIED_WITH_SUGGESTIONS", "PARTIALLY_VERIFIED")
        for s in p.sections:
            total_evidence_refs += len(s.evidence_refs)
            for c in s.claims:
                if "VERIFIED" in str(c.verdict):
                    total_verified_claims += 1

    assert total_verified_claims > 0, "No claims were verified across PetClinic documentation"
    assert total_evidence_refs > 0, "No EvidenceRefs were attached to PetClinic documentation"

    print(f"  🟢 Spring PetClinic Wiki Verified: {len(pages)} pages, {total_verified_claims} verified claims, {total_evidence_refs} source citations.")
    print("Integration Test PetClinic Wiki Complete: 100% Passed\n")


if __name__ == "__main__":
    test_wiki_petclinic()
