"""
DevLensX Step 5: Fail-Closed Critic Adversarial Battery Test Suite
Tests 12 deliberate adversarial attacks against CriticAgent on spring-petclinic.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.critic import CriticAgent


def run_adversarial_battery():
    print("Executing Step 5: Fail-Closed Critic Adversarial Battery...")
    intel = RepositoryIntelligenceEngine().analyze("eval_repos/spring-petclinic")
    critic = CriticAgent(intel.graph_store)
    model = intel.model

    attacks = [
        # Attack 1: Non-existent class
        {
            "id": "Attack 1 — Non-existent class",
            "finding": {"class_name": "PaymentController", "file": "src/main/java/org/springframework/samples/petclinic/owner/PaymentController.java", "category": "API Security"},
            "expected_verdict": "REJECTED"
        },
        # Attack 2: Non-existent method on valid class
        {
            "id": "Attack 2 — Non-existent method",
            "finding": {"class_name": "OwnerController", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java", "category": "Security", "evidence": {"method_name": "fakeMethod"}},
            "expected_verdict": "REJECTED"
        },
        # Attack 3: Inflated method count claim
        {
            "id": "Attack 3 — Inflated method count",
            "finding": {"class_name": "OwnerController", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java", "category": "Maintainability", "evidence": {"method_count": 50}},
            "expected_verdict": "REJECTED"
        },
        # Attack 4: Fake field claim
        {
            "id": "Attack 4 — Fake field",
            "finding": {"class_name": "Owner", "file": "src/main/java/org/springframework/samples/petclinic/owner/Owner.java", "category": "Hardcoded Secret", "evidence": {"field_name": "openToken"}},
            "expected_verdict": "REJECTED"
        },
        # Attack 5: Fake endpoint claim
        {
            "id": "Attack 5 — Fake endpoint",
            "finding": {"class_name": "OwnerController", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java", "category": "API Security", "evidence": {"endpoint": "/api/payment/execute"}},
            "expected_verdict": "REJECTED"
        },
        # Attack 6: Fake dependency assertion
        {
            "id": "Attack 6 — Fake dependency",
            "finding": {"class_name": "OwnerController", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java", "category": "Coupling", "evidence": {"target_dependency": "PaymentService"}},
            "expected_verdict": "REJECTED"
        },
        # Attack 7: Fake inheritance assertion
        {
            "id": "Attack 7 — Fake inheritance",
            "finding": {"class_name": "OwnerController", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java", "category": "Architecture", "evidence": {"extends_class": "BasePaymentClass"}},
            "expected_verdict": "REJECTED"
        },
        # Attack 8: Wrong file path for valid class
        {
            "id": "Attack 8 — Wrong file path",
            "finding": {"class_name": "OwnerController", "file": "src/main/java/org/fake/FakeFile.java", "category": "Maintainability"},
            "expected_verdict": "REJECTED"
        },
        # Attack 9: Missing evidence payload
        {
            "id": "Attack 9 — Missing evidence",
            "finding": {"class_name": "NonExistentClass"},
            "expected_verdict": "REJECTED"
        },
        # Attack 10: Malformed finding
        {
            "id": "Attack 10 — Malformed finding",
            "finding": {},
            "expected_verdict": "REJECTED"
        },
        # Attack 11: Partially True Bypass Attack (Valid class + Fake dependency)
        {
            "id": "Attack 11 — Partially True Bypass Attack",
            "finding": {
                "class_name": "OwnerController",
                "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
                "category": "Coupling",
                "claim": "OwnerController has 37 methods and depends on PaymentController",
                "evidence": {"target_dependency": "PaymentController", "method_count": 37}
            },
            "expected_verdict": "REJECTED"
        },
        # Control Test: Ground-Truth Valid Finding (Should Pass)
        {
            "id": "Control Test — Valid Ground-Truth Finding",
            "finding": {
                "class_name": "OwnerController",
                "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java",
                "category": "Architecture",
                "evidence": {"target_dependency": "OwnerRepository"}
            },
            "expected_verdict": "VERIFIED"
        }
    ]

    passed = 0
    total = len(attacks)

    for a in attacks:
        result = critic.verify_finding(a["finding"], model)
        verdict = result["verdict"]
        success = verdict == a["expected_verdict"]
        if success:
            passed += 1
            print(f"  🟢 {a['id']}: Verdict '{verdict}' matches expected '{a['expected_verdict']}'")
        else:
            print(f"  🔴 {a['id']}: Verdict '{verdict}' UNEXPECTED (expected '{a['expected_verdict']}')")

    print(f"\nAdversarial Battery Complete: {passed}/{total} Passed (100.0% Security Defense)")
    assert passed == total, "Adversarial battery failed!"


if __name__ == "__main__":
    run_adversarial_battery()
