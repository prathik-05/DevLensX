"""
DevLensX Unit Test Suite: D7.5 Documentation Verification Engine
Verifies that PageVerifier evaluates candidate claims against AST and graph evidence,
attaching EvidenceRefs to VERIFIED claims and rejecting unevidenced assertions.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.critic.claim_verifier import AtomicClaim, ClaimVerdict
from devlensx.documentation.page_verifier import PageVerifier


def test_documentation_verification():
    print("Executing Unit Test: D7.5 Documentation Verification...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_verify_test_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    claims = [
        AtomicClaim(subject="OwnerController", predicate="depends on", object="OwnerRepository", claim_type="structural"),
        AtomicClaim(subject="System", predicate="suggests", object="Redis caching", claim_type="suggestion"),
        AtomicClaim(subject="FakePaymentService", predicate="calls", object="StripeGateway", claim_type="invocation"),
    ]

    v_claims, v_refs, verdict = PageVerifier.verify_section_claims(
        raw_claims=claims,
        snapshot=snapshot,
        classes=intel.model.get("classes", []),
        relationships=intel.model.get("relationships", []),
    )

    # 1. Fact Check: OwnerController -> OwnerRepository
    fact_claim = next(c for c in v_claims if c.subject == "OwnerController")
    assert fact_claim.verdict == ClaimVerdict.VERIFIED
    assert len(v_refs) > 0
    assert any("OwnerController" in r.file_path for r in v_refs)

    # 2. Suggestion Check
    sug_claim = next(c for c in v_claims if c.claim_type == "suggestion")
    assert sug_claim.verdict == ClaimVerdict.PARTIAL

    # 3. Unevidenced Assertion: FakePaymentService -> StripeGateway
    fake_claim = next(c for c in v_claims if c.subject == "FakePaymentService")
    assert fake_claim.verdict == ClaimVerdict.UNSUPPORTED

    print("  🟢 Documentation Verification Verified: Verified facts carry EvidenceRefs; unevidenced claims fail closed.")
    print("Unit Test Documentation Verification Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_verification()
