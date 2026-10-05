"""Intent classifier for chat modes — lightweight, deterministic."""

from devlensx.chat.models import ChatIntent


def classify_intent(message: str) -> ChatIntent:
    q = (message or "").lower()
    # Fake tech queries should be EXPLANATION, not architecture
    if any(k in q for k in ("redis", "kafka", "mongodb", "postgres", "paymentservice", "fakecontroller")):
        return ChatIntent.EXPLANATION
    if any(k in q for k in ("deep research", "complete analysis", "comprehensive", "architecture", "security risks", "change it", "files i would need")):
        return ChatIntent.RESEARCH
    if any(k in q for k in ("codemap", "request reaches", "trace", "flow to", "reach the database", "call graph", "how does", "explain how")):
        if "trace" in q or "reach" in q or "flow" in q:
            return ChatIntent.CODEMAP_REQUEST
        if "change" in q or "impact" in q:
            return ChatIntent.CHANGE_IMPACT
        return ChatIntent.ARCHITECTURE
    if any(k in q for k in ("where is", "authentication", "auth", "security", "vulnerability")):
        return ChatIntent.SECURITY
    if any(k in q for k in ("overview", "what is", "summary", "getting started", "project does")):
        return ChatIntent.OVERVIEW
    if "redis" in q or "kafka" in q or "mongodb" in q or "postgres" in q:
        return ChatIntent.EXPLANATION
    return ChatIntent.EXPLANATION