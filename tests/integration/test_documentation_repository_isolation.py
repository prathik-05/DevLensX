"""
DevLensX Integration Test Suite: D7 Cross-Repository Documentation Isolation
Verifies that generated documentation for Repo A never leaks symbols, citations, or diagrams from Repo B.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.documentation.page_generator import DocumentationPageGenerator


def test_documentation_repository_isolation():
    print("Executing Integration Test: D7 Cross-Repository Documentation Isolation...")

    # 1. Generate Spring PetClinic documentation
    pet_path = os.path.abspath("eval_repos/spring-petclinic")
    pet_intel = RepositoryIntelligenceEngine().analyze(pet_path)
    pet_snap = register_snapshot(
        repository_id="spring-petclinic",
        analysis_run_id="run_iso_pet_001",
        repo_path=pet_path,
        commit_hash="c0ffee1",
    )
    pet_gen = DocumentationPageGenerator(pet_snap, pet_intel.model)
    pet_pages = pet_gen.generate_all_pages()

    # 2. Generate sp-portfolio documentation
    ts_path = os.path.abspath("eval_repos/sp-portfolio")
    ts_intel = RepositoryIntelligenceEngine().analyze(ts_path)
    ts_snap = register_snapshot(
        repository_id="sp-portfolio",
        analysis_run_id="run_iso_ts_001",
        repo_path=ts_path,
        commit_hash="c0ffee2",
    )
    ts_gen = DocumentationPageGenerator(ts_snap, ts_intel.model)
    ts_pages = ts_gen.generate_all_pages()

    # 3. Assert PetClinic contains NO TS symbols or citations
    pet_all_text = " ".join(" ".join(s.content for s in p.sections) for p in pet_pages)
    assert "SPDevProvider" not in pet_all_text
    assert "VenomMetaballs" not in pet_all_text

    for p in pet_pages:
        assert p.repository_id == "spring-petclinic"
        assert p.analysis_run_id == "run_iso_pet_001"
        for s in p.sections:
            for ref in s.evidence_refs:
                assert ref.repository_id == "spring-petclinic"
                assert not ref.file_path.endswith((".ts", ".tsx"))

    # 4. Assert TS portfolio contains NO Java symbols or citations
    ts_all_text = " ".join(" ".join(s.content for s in p.sections) for p in ts_pages)
    assert "OwnerController" not in ts_all_text
    assert "PetRepository" not in ts_all_text

    for p in ts_pages:
        assert p.repository_id == "sp-portfolio"
        assert p.analysis_run_id == "run_iso_ts_001"
        for s in p.sections:
            for ref in s.evidence_refs:
                assert ref.repository_id == "sp-portfolio"
                assert not ref.file_path.endswith(".java")

    print("  🟢 Cross-Repository Isolation Verified: No cross-contamination of symbols, citations, or run IDs.")
    print("Integration Test Repository Isolation Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_repository_isolation()
