import sys
sys.path.insert(0, '.')
from devlensx.chat.research_planner import plan_research

def test_deep_research_planner():
    subs = plan_research("Explain the complete authentication architecture")
    assert len(subs) == 6
    assert any("configured" in s for s in subs)
    assert any("endpoints" in s for s in subs)
    print("planner ok")