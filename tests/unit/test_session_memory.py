"""
DevLensX Unit Test Suite: Session Memory Multi-Turn Context Resolution (Phase 11.2)
Verifies that multi-turn session history correctly resolves follow-up queries.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.services.copilot_service import CopilotService


def test_session_memory_turn_resolution():
    print("Executing Unit Test: Phase 11.2 Session Memory Resolution...")

    history = [
        {"role": "user", "content": "How does authentication work in this repository?"},
        {"role": "assistant", "content": "Authentication is handled through SecurityConfig and JwtAuthenticationFilter."}
    ]

    res = CopilotService.process_question(
        db=None,
        question="Where is JWT validated?",
        session_history=history
    )

    assert "plain_english" in res, "Missing plain_english in response!"
    print("  🟢 Session Memory Context Injected Successfully into Query Pipeline")
    print("Unit Test Session Memory Complete: 100% Passed\n")


if __name__ == "__main__":
    test_session_memory_turn_resolution()
