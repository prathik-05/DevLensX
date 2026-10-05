"""
DevLensX Unit Test Suite: Root Cause Center Engine (Phase B)
Verifies stack trace mapping against AST nodes with strict badge boundaries.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.services.debug_service import DebugRootCauseEngine


def test_root_cause_engine_trace_analysis():
    print("Executing Unit Test: Phase B Root Cause Center Engine...")

    sample_model = {
        "classes": [
            {"name": "OwnerController", "file": "src/main/java/org/petclinic/owner/OwnerController.java"},
            {"name": "OwnerRepository", "file": "src/main/java/org/petclinic/owner/OwnerRepository.java"}
        ]
    }

    sample_trace = (
        "java.lang.NullPointerException: Cannot invoke Owner.getFirstName()\n"
        "\tat org.petclinic.owner.OwnerController.processFindForm(OwnerController.java:110)\n"
        "\tat org.petclinic.owner.OwnerRepository.findByLastName(OwnerRepository.java:45)"
    )

    res = DebugRootCauseEngine.analyze_stack_trace(sample_trace, sample_model)

    assert res["status"] == "success", "Root Cause Analysis failed!"
    assert len(res["verified_locations"]) == 2, "Failed to map all 2 stack trace locations!"
    assert res["verified_locations"][0]["status"] == "🟢 VERIFIED BY AST"
    assert "🔵 AI SUGGESTION" in res["ai_hypothesis"]["badge"]
    assert "⚪ NOT VERIFIED" in res["not_verified_boundary"]["badge"]

    print("  🟢 Root Cause Center Stack Trace Mapping Passed with Strict Badge Boundaries")
    print("Unit Test Root Cause Engine Complete: 100% Passed\n")


if __name__ == "__main__":
    test_root_cause_engine_trace_analysis()
