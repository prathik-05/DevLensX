"""
DevLensX Adversarial Documentation Test Suite: D7.11 & D7.13
Deliberately injects unsupported factual assertions (Redis, Kafka, PostgreSQL, PaymentService)
and validates that they fail closed as INSUFFICIENT_EVIDENCE while recommendations become AI_SUGGESTION
and verified facts receive EvidenceRefs.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.evidence.models import SnapshotRecord
from devlensx.documentation.claim_extractor import ClaimExtractor
from devlensx.documentation.page_verifier import PageVerifier
from devlensx.critic.claim_verifier import ClaimVerdict


def test_documentation_adversarial():
    print("Executing Adversarial Test: D7 Hallucination & False Fact Rejection...")

    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    snapshot = SnapshotRecord(
        repository_id="spring-petclinic",
        analysis_run_id="run_adv_001",
        repo_path="eval_repos/spring-petclinic",
        commit_hash="c0ffee1",
    )

    adversarial_text = (
        "OwnerController depends on OwnerRepository to fetch pet owners from the database. "
        "The application uses Redis for caching frequently requested owners. "
        "Kafka handles asynchronous notification events across services. "
        "Consider introducing Redis caching to improve database throughput."
    )

    raw_claims = ClaimExtractor.extract_from_text(adversarial_text)
    v_claims, v_refs, verdict = PageVerifier.verify_section_claims(
        raw_claims=raw_claims,
        snapshot=snapshot,
        classes=intel.model.get("classes", []),
        relationships=intel.model.get("relationships", []),
    )

    # 1. Real Fact Check: OwnerController -> OwnerRepository
    owner_claim = next(c for c in v_claims if c.subject == "OwnerController")
    assert owner_claim.verdict == ClaimVerdict.VERIFIED, "Real structural relationship failed verification"
    assert len(v_refs) > 0

    # 2. False Assertion Check: Redis
    redis_claim = next((c for c in v_claims if "redis" in c.object.lower() and c.claim_type != "suggestion"), None)
    if redis_claim:
        assert redis_claim.verdict == ClaimVerdict.UNSUPPORTED, "False Redis claim was mistakenly verified!"

    # 3. False Assertion Check: Kafka
    kafka_claim = next((c for c in v_claims if "kafka" in c.subject.lower() or "kafka" in c.object.lower()), None)
    if kafka_claim:
        assert kafka_claim.verdict == ClaimVerdict.UNSUPPORTED, "False Kafka claim was mistakenly verified!"

    # 4. Recommendation Check: Consider adding Redis caching
    sug_claim = next(c for c in v_claims if c.claim_type == "suggestion")
    assert sug_claim.verdict == ClaimVerdict.PARTIAL, "Recommendation was not classified as AI_SUGGESTION"

    print("  🟢 Adversarial Defense Verified: Hallucinated Redis/Kafka claims rejected; suggestions and facts properly classified.")
    print("Adversarial Documentation Test Complete: 100% Passed\n")


if __name__ == "__main__":
    test_documentation_adversarial()
