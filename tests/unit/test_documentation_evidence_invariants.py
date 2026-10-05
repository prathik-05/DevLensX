"""
DevLensX Unit Test Suite: D7.11 Documentation Evidence Invariants
Verifies hard invariant contract:
- VERIFIED claims MUST have >= 1 EvidenceRef
- INSUFFICIENT_EVIDENCE claims have NO fake EvidenceRefs
- AI_SUGGESTION claims are explicitly tagged
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.documentation.models import DocumentationPage, DocumentationSection, PageStatus
from devlensx.critic.claim_verifier import AtomicClaim, ClaimVerdict
from devlensx.evidence.models import EvidenceRef, EvidenceType


def test_documentation_evidence_invariants():
    print("Executing Unit Test: D7.11 Documentation Evidence Invariants...")

    ref1 = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id="run_inv_001",
        file_path="src/main/java/org/samples/petclinic/owner/OwnerController.java",
        line_start=23,
        line_end=110,
        commit_hash="c0ffee1",
        symbol_name="OwnerController",
    )

    # 1. Valid Verified Section
    sec_verified = DocumentationSection(
        heading="Owner Controller Section",
        content="OwnerController handles web requests.",
        claims=[AtomicClaim(subject="OwnerController", predicate="handles", object="requests", claim_type="endpoint", verdict=ClaimVerdict.VERIFIED)],
        evidence_refs=[ref1],
        verdict="VERIFIED",
    )

    # 2. Suggestion Section
    sec_suggestion = DocumentationSection(
        heading="Optimization Suggestions",
        content="Consider adding Redis caching.",
        claims=[AtomicClaim(subject="System", predicate="suggests", object="Redis caching", claim_type="suggestion", verdict=ClaimVerdict.PARTIAL)],
        evidence_refs=[],
        verdict="AI_SUGGESTION",
    )

    # 3. Insufficient Evidence Section
    sec_insufficient = DocumentationSection(
        heading="Database Subsystem",
        content="Uses Cassandra NoSQL.",
        claims=[AtomicClaim(subject="System", predicate="uses", object="Cassandra", claim_type="structural", verdict=ClaimVerdict.UNSUPPORTED)],
        evidence_refs=[],
        verdict="INSUFFICIENT_EVIDENCE",
    )

    page = DocumentationPage(
        id="arch",
        title="Architecture",
        purpose="System architecture",
        repository_id="spring-petclinic",
        analysis_run_id="run_inv_001",
        commit_hash="c0ffee1",
        sections=[sec_verified, sec_suggestion, sec_insufficient],
    )

    page.validate_invariants()
    assert page.status == PageStatus.PARTIALLY_VERIFIED
    assert page.verification_summary["verified"] == 1
    assert page.verification_summary["suggestions"] == 1
    assert page.verification_summary["insufficient_evidence"] == 1

    # Invariant: Section claiming VERIFIED with no EvidenceRefs gets downgraded to INSUFFICIENT_EVIDENCE
    bad_section = DocumentationSection(
        heading="Bad Section",
        content="Claims verified without proof.",
        claims=[],
        evidence_refs=[],
        verdict="VERIFIED",
    )
    page_bad = DocumentationPage(
        id="bad",
        title="Bad Page",
        purpose="Bad purpose",
        repository_id="spring-petclinic",
        analysis_run_id="run_inv_001",
        commit_hash="c0ffee1",
        sections=[bad_section],
    )
    page_bad.validate_invariants()
    assert bad_section.verdict == "INSUFFICIENT_EVIDENCE"

    print("  🟢 Evidence Invariants Verified: Invariant rules strictly enforced.")
    print("Unit Test Evidence Invariants Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_evidence_invariants()
