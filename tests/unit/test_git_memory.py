"""
DevLensX Unit Test Suite: Phase 11.5 Git Memory Subsystem
Tests checkable git facts and keyword-based fix commit heuristics.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.git.git_memory import GitMemoryEngine


def test_git_memory_extraction():
    print("Executing Unit Test: Phase 11.5 Git Memory Subsystem...")

    res = GitMemoryEngine.analyze_file_history(".", "README.md")
    assert "commit_count" in res, "Missing commit_count in Git Memory output!"
    assert "heuristics" in res, "Missing heuristics in Git Memory output!"
    assert res["label"] == "Fact (Checkable via git log)"
    print("  🟢 Git Memory Fact & Heuristic Extraction Passed")
    print("Unit Test Git Memory Complete: 100% Passed\n")


if __name__ == "__main__":
    test_git_memory_extraction()
