"""
DevLensX Unit Test Suite: Claim-Level Critic Verification Engine
Verifies atomic claim resolution (subject, predicate, object) against AST & Cypher graph edges.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.critic.claim_verifier import ClaimVerifierEngine, ClaimVerdict


def test_claim_verifier():
    print("Executing Unit Test: Claim-Level Critic Verification Engine...")

    classes = [
        {
            "name": "OwnerController",
            "stereotype": "Controller",
            "file": "OwnerController.java",
            "line_start": 23,
            "injected_dependencies": ["OwnerRepository"]
        },
        {
            "name": "OwnerRepository",
            "stereotype": "Repository",
            "file": "OwnerRepository.java",
            "line_start": 10,
            "injected_dependencies": []
        }
    ]

    graph_edges = [
        {"source": "OwnerController", "target": "OwnerRepository", "type": "DEPENDS_ON"}
    ]

    # AI text containing 1 verified claim and 1 unsupported hallucinated claim
    ai_response = (
        "OwnerController depends on OwnerRepository to fetch pet owners. "
        "Additionally, Redis manages session caching across instances."
    )

    result = ClaimVerifierEngine.extract_and_verify_claims(ai_response, classes, graph_edges)

    # 1. Verify structural claim
    assert result["verified_claims_count"] >= 1
    verified_claim = result["verified_claims"][0]
    assert verified_claim["subject"] == "OwnerController"
    assert verified_claim["object"] == "OwnerRepository"
    assert verified_claim["verdict"] == ClaimVerdict.VERIFIED.value
    print(f"  🟢 Verified Structural Claim: {verified_claim['subject']} -> {verified_claim['object']} ({verified_claim['evidence']})")

    # 2. Verify unsupported hallucination detection
    assert result["unsupported_claims_count"] >= 1
    unsupported_claim = result["unsupported_claims"][0]
    assert unsupported_claim["subject"] == "Redis"
    assert unsupported_claim["verdict"] == ClaimVerdict.UNSUPPORTED.value
    print(f"  🔴 Intercepted Hallucinated Claim: {unsupported_claim['subject']} ({unsupported_claim['evidence']})")

    print("Unit Test Claim-Level Verifier Complete: 100% Passed\n")


if __name__ == "__main__":
    test_claim_verifier()
