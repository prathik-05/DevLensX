import sys
sys.path.insert(0, '.')
from devlensx.chat.intent import classify_intent
from devlensx.chat.models import ChatIntent

def test_chat_intent():
    assert classify_intent("Where is authentication implemented?") == ChatIntent.SECURITY
    assert classify_intent("Trace the owner request to persistence") == ChatIntent.CODEMAP_REQUEST
    assert classify_intent("Explain the complete authentication architecture including configuration") == ChatIntent.RESEARCH
    assert classify_intent("What is this repository?") == ChatIntent.OVERVIEW
    assert classify_intent("How does Redis handle caching?") == ChatIntent.EXPLANATION
    print("intent ok")