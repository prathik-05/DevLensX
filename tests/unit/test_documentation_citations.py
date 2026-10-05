"""
DevLensX Unit Test Suite: D7.6 Documentation Citations & D5 Resolution
Verifies that documentation claims produce valid citations that resolve through SnapshotRegistry.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.resolver import register_snapshot, get_evidence_resolver
from devlensx.documentation.page_generator import DocumentationPageGenerator


def test_documentation_citations():
    print("Executing Unit Test: D7.6 Documentation Citations & D5 Resolution...")

    repo_path = os.path.abspath("eval_repos/spring-petclinic")
    intel = RepositoryIntelligenceEngine().analyze(repo_path)
    snapshot = register_snapshot(
        repository_id="spring-petclinic",
        analysis_run_id="run_doc_cit_001",
        repo_path=repo_path,
        commit_hash="c0ffee1",
    )

    gen = DocumentationPageGenerator(snapshot, intel.model)
    blueprint = {
        "id": "owners",
        "title": "Owner Subsystem",
        "purpose": "Owner workflows",
        "target_symbols": ["OwnerController"],
    }
    page = gen.generate_page(blueprint)

    resolver = get_evidence_resolver()
    all_refs = []
    for sec in page.sections:
        all_refs.extend(sec.evidence_refs)

    assert len(all_refs) > 0, "No EvidenceRefs attached to generated page sections"

    # Resolve all EvidenceRefs
    for ref in all_refs:
        res = resolver.resolve(ref)
        assert res.resolved is True, f"Failed to resolve citation: {ref.to_citation()}"
        assert len(res.lines) > 0

    print(f"  🟢 Citations Verified: Successfully resolved {len(all_refs)} section EvidenceRefs through D5.")
    print("Unit Test Documentation Citations Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_citations()
