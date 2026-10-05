"""
DevLensX Unit Test Suite: Build Studio Refinement Engine (Phase B)
Verifies explainable blast-radius change impact calculation with strict badge boundaries.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.services.build_studio_service import BuildStudioEngine


def test_build_studio_change_impact():
    print("Executing Unit Test: Phase B Build Studio Refinement Engine...")

    sample_model = {
        "classes": [
            {
                "name": "OwnerController",
                "file": "src/main/java/org/petclinic/owner/OwnerController.java",
                "package": "org.petclinic.owner",
                "injected_dependencies": ["OwnerRepository", "ClinicService"]
            }
        ]
    }

    res = BuildStudioEngine.calculate_change_impact("OwnerController", sample_model)

    assert res["target"] == "OwnerController"
    assert res["directly_affected"][0]["status"] == "🟢 VERIFIED BY AST"
    assert len(res["dependents"]) == 2
    assert res["dependents"][0]["status"] == "🟢 VERIFIED BY KUZU GRAPH"
    assert res["affected_capability"]["status"] == "🟢 VERIFIED FEATURE MEMORY"
    assert "🔵 AI SUGGESTION" in res["ai_suggestion"]["badge"]

    print("  🟢 Build Studio Change Impact Blast-Radius Calculated with Strict Badge Boundaries")
    print("Unit Test Build Studio Complete: 100% Passed\n")


if __name__ == "__main__":
    test_build_studio_change_impact()
