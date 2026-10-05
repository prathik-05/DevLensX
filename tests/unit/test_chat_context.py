import sys
sys.path.insert(0, '.')
from devlensx.chat.context import build_context_query, describe_context
from devlensx.chat.models import ChatContext

def test_chat_context():
    ctx = ChatContext(repository_id="r", analysis_run_id="a", selected_symbol="OwnerController", page_id="core-architecture")
    q = build_context_query(ctx, "Explain this")
    assert "symbol:OwnerController" in q or "source:OwnerController" in q
    assert "page:core-architecture" in q
    desc = describe_context(ctx)
    assert desc["level"] == "source"
    assert "OwnerController" in desc["priority"][0]
    # Priority: source > diagram > section > page > repo
    ctx2 = ChatContext(repository_id="r", analysis_run_id="a", page_id="overview")
    assert describe_context(ctx2)["level"] == "page"
    print("context ok")