"""
DevLensX Unit Test Suite: Phase 11.3 Feature Memory Subsystem
Tests domain feature extraction without assuming Controller->Service->Repository patterns.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.understanding.intelligence.feature_memory import FeatureMemoryEngine


def test_feature_memory_extraction():
    print("Executing Unit Test: Phase 11.3 Feature Memory Subsystem...")

    # Layered Spring PetClinic classes
    classes_layered = [
        {"name": "OwnerController", "package": "org.petclinic.owner", "stereotype": "Controller", "endpoints": ["/owners"]},
        {"name": "OwnerRepository", "package": "org.petclinic.owner", "stereotype": "Repository"},
        {"name": "Owner", "package": "org.petclinic.owner", "stereotype": "Entity"}
    ]

    feats_layered = FeatureMemoryEngine.extract_features(classes_layered)
    assert len(feats_layered) > 0
    assert feats_layered[0]["name"] == "Owner"
    assert "/owners" in feats_layered[0]["endpoints"]
    print("  🟢 Layered Domain Feature Extraction Passed")

    # Unstructured script classes
    classes_unstructured = [
        {"name": "App", "package": "com.app", "stereotype": "General"},
        {"name": "Auth", "package": "com.app", "stereotype": "General"}
    ]

    feats_unstructured = FeatureMemoryEngine.extract_features(classes_unstructured)
    assert len(feats_unstructured) > 0
    print("  🟢 Unstructured Repository Feature Extraction Passed")
    print("Unit Test Feature Memory Complete: 100% Passed\n")


if __name__ == "__main__":
    test_feature_memory_extraction()
