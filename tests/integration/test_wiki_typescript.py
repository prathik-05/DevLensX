"""
DevLensX Integration Test Suite: D7 TypeScript (sp-portfolio) Wiki Generation
Verifies documentation generation on real TypeScript / React repository without Java/Spring assumptions.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.documentation.page_generator import DocumentationPageGenerator


def test_wiki_typescript():
    print("Executing Integration Test: D7 TypeScript (sp-portfolio) Wiki Generation...")

    repo_path = os.path.abspath("eval_repos/sp-portfolio")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    snapshot = register_snapshot(
        repository_id="sp-portfolio",
        analysis_run_id="run_ts_wiki_001",
        repo_path=repo_path,
        commit_hash="c0ffee1",
    )

    gen = DocumentationPageGenerator(snapshot, intel.model, retriever=intel.retriever)
    pages = gen.generate_all_pages()

    assert len(pages) >= 2
    # Verify no hardcoded Java / Spring Boot artifacts leak into TypeScript docs
    all_content = " ".join(" ".join(s.content for s in p.sections) for p in pages)
    assert "@SpringBootApplication" not in all_content
    assert "org.springframework" not in all_content

    # Check evidence citations resolve to .ts / .tsx files
    ts_citations = 0
    for p in pages:
        for s in p.sections:
            for ref in s.evidence_refs:
                if ref.file_path.endswith((".ts", ".tsx", ".js", ".jsx", ".json", ".md")):
                    ts_citations += 1

    assert ts_citations > 0, "No TypeScript source files cited in sp-portfolio documentation"

    print(f"  🟢 TypeScript Wiki Verified: {len(pages)} pages generated with {ts_citations} TypeScript citations.")
    print("Integration Test TypeScript Wiki Complete: 100% Passed\n")


if __name__ == "__main__":
    test_wiki_typescript()
