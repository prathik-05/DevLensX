"""
DevLensX Unit Tests: Capability Detector & Honest Ambiguity Protocol
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.understanding.intelligence.capability_detector import CapabilityDetector
from devlensx.understanding.model.repository_brain import RepositoryBrain


def test_capability_detector_honest_ambiguity():
    # Small repository with 2 classes
    small_classes = [
        {"name": "Main", "package": "com.example", "stereotype": "General"},
        {"name": "Util", "package": "com.example", "stereotype": "General"}
    ]
    caps = CapabilityDetector.detect_capabilities(small_classes)
    assert len(caps) == 1
    assert "Ambiguous" in caps[0]["capability"], "Honest ambiguity protocol failed!"
    print("  🟢 Unit Test: Capability Detector Honest Ambiguity Passed")


def test_repository_brain_snapshot():
    classes = [
        {"name": "OwnerController", "package": "org.petclinic.owner", "stereotype": "Controller"},
        {"name": "OwnerRepository", "package": "org.petclinic.owner", "stereotype": "Repository"}
    ]
    brain = RepositoryBrain("eval_repos/spring-petclinic", classes)
    assert brain.analysis_run_id.startswith("run_")
    assert "OwnerController" in brain.symbols
    assert len(brain.endpoints) == 1
    print("  🟢 Unit Test: Repository Brain Snapshot Contract Passed")


if __name__ == "__main__":
    print("Running Unit Test Suite: Understanding & Brain...")
    test_capability_detector_honest_ambiguity()
    test_repository_brain_snapshot()
    print("Unit Test Suite Understanding Complete: 100% Passed\n")
