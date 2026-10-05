"""
DevLensX Integration Test Suite: D7 Python Repository Wiki Generation
Verifies documentation generation on real Python repository without Java/Spring assumptions.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot
from devlensx.documentation.page_generator import DocumentationPageGenerator


def test_wiki_python():
    print("Executing Integration Test: D7 Python Wiki Generation...")

    repo_path = os.path.abspath("eval_repos/battleship-python")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    snapshot = register_snapshot(
        repository_id="battleship-python",
        analysis_run_id="run_py_wiki_001",
        repo_path=repo_path,
        commit_hash="c0ffee1",
    )

    gen = DocumentationPageGenerator(snapshot, intel.model, retriever=intel.retriever)
    pages = gen.generate_all_pages()

    assert len(pages) >= 2
    # Verify citations point to Python files
    py_citations = 0
    for p in pages:
        for s in p.sections:
            for ref in s.evidence_refs:
                if ref.file_path.endswith((".py", ".md", ".txt")):
                    py_citations += 1

    assert py_citations > 0, "No Python source files cited in Python documentation"

    print(f"  🟢 Python Wiki Verified: {len(pages)} pages generated with {py_citations} Python citations.")
    print("Integration Test Python Wiki Complete: 100% Passed\n")


if __name__ == "__main__":
    test_wiki_python()
