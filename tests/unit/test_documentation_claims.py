"""
DevLensX Unit Test Suite: D7.4 Claim Extractor
Verifies that ClaimExtractor extracts candidate claims without performing verification.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.documentation.claim_extractor import ClaimExtractor
from devlensx.critic.claim_verifier import ClaimVerdict


def test_documentation_claims():
    print("Executing Unit Test: D7.4 Claim Extractor...")

    sample_prose = (
        "OwnerController delegates to OwnerRepository for database queries. "
        "VetController calls VetService to retrieve veterinarian schedules. "
        "Consider adding Redis for caching frequently accessed records."
    )

    claims = ClaimExtractor.extract_from_text(sample_prose)
    assert len(claims) >= 3

    # Check structural extraction
    c1 = next((c for c in claims if c.subject == "OwnerController"), None)
    assert c1 is not None
    assert c1.object == "OwnerRepository"
    assert c1.verdict == ClaimVerdict.UNSUPPORTED  # Invariant: ClaimExtractor must NOT verify

    # Check suggestion extraction
    sug = next((c for c in claims if c.claim_type == "suggestion"), None)
    assert sug is not None
    assert sug.verdict == ClaimVerdict.PARTIAL

    print("  🟢 Claim Extractor Verified: Extracted candidate claims without performing early verification.")
    print("Unit Test Claim Extractor Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_claims()
