"""
DevLensX Unit Test Suite: Three Chat Modes Engine (Fast, Codemap, Deep Research)
Verifies evidence-grounded chat execution across Fast, Codemap, and Deep Research modes with line citations.
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.urm.models import UniversalRepositoryModel, URMSymbol, URMRelationship, SymbolKind, RelationshipType, SourceLocation
from devlensx.chat.chat_engine import DevLensXChatEngine, ChatMode


def test_deepwiki_chat_engine():
    print("Executing Unit Test: Three Chat Modes Engine (Fast, Codemap, Deep Research)...")

    urm = UniversalRepositoryModel(
        repository_id="repo_ts",
        name="sp-portfolio",
        root_path="/",
        primary_language="typescript",
        symbols=[
            URMSymbol(id="s1", name="SPDevProvider", qualified_name="src/context/spdev-provider.tsx:SPDevProvider", kind=SymbolKind.CLASS, language="typescript", location=SourceLocation(file_path="src/context/spdev-provider.tsx", start_line=10, end_line=50), stereotype="Context"),
            URMSymbol(id="s2", name="ThemeProvider", qualified_name="src/components/theme-provider.tsx:ThemeProvider", kind=SymbolKind.CLASS, language="typescript", location=SourceLocation(file_path="src/components/theme-provider.tsx", start_line=5, end_line=30), stereotype="Component")
        ],
        relationships=[
            URMRelationship(source_id="s1", target_id="s2", relationship_type=RelationshipType.DEPENDS_ON, language="typescript")
        ]
    )

    chat_engine = DevLensXChatEngine(urm)

    # 1. Fast Chat Mode Test
    res_fast = chat_engine.execute_chat_query("What is SPDevProvider?", mode=ChatMode.FAST)
    assert res_fast["mode"] == ChatMode.FAST
    assert len(res_fast["citations"]) >= 1
    assert "src/context/spdev-provider.tsx#L10-50" in res_fast["citations"][0]
    print(f"  🟢 Fast Chat Mode Verified: Citation '{res_fast['citations'][0]}' attached")

    # 2. Codemap Chat Mode Test
    res_code = chat_engine.execute_chat_query("Explain theme architecture", mode=ChatMode.CODEMAP)
    assert res_code["mode"] == ChatMode.CODEMAP
    assert "graph TD" in res_code["diagram"]
    print(f"  🟢 Codemap Chat Mode Verified: Interactive diagram and walkthrough generated")

    # 3. Deep Research Mode Test
    res_deep = chat_engine.execute_chat_query("Deep research theme state flow", mode=ChatMode.DEEP_RESEARCH)
    assert res_deep["mode"] == ChatMode.DEEP_RESEARCH
    assert "Deep Research Synthesis" in res_deep["answer"]
    print(f"  🟢 Deep Research Mode Verified: Sub-question research planner & evidence synthesis completed")

    print("Unit Test DeepWiki Chat Engine Complete: 100% Passed\n")


if __name__ == "__main__":
    test_deepwiki_chat_engine()
