"""Intent classifier for chat modes — lightweight, deterministic."""

from devlensx.chat.models import ChatIntent


def classify_intent(message: str) -> ChatIntent:
    q = (message or "").lower()
    # High-priority overview and repo comprehension queries
    if any(k in q for k in ("overview", "what is this repository", "what does this project do", "what does this repository do", "what does this application do", "what does this app do", "what does this codebase do", "summary", "getting started", "project does", "about")):
        return ChatIntent.OVERVIEW
    # Fake tech queries should be EXPLANATION, not architecture
    if any(k in q for k in ("redis", "kafka", "mongodb", "postgres", "paymentservice", "fakecontroller")):
        return ChatIntent.EXPLANATION
    if any(k in q for k in ("persistence", "persisted", "repositories", "dao", "database", "schema", "table", "data flow", "data validated", "storage", "implements repository")):
        return ChatIntent.DATA_FLOW
    if any(k in q for k in ("which tests", "test coverage", "unit test", "test suite", "covered by tests", "assert")):
        return ChatIntent.TESTING
    if any(k in q for k in ("authentication", "auth", "security risks", "security vulnerability", "vulnerability", "jwt", "login", "password")):
        return ChatIntent.SECURITY
    if any(k in q for k in ("where should i edit", "where do i edit", "where to change", "how do i change", "how do i add", "where to modify", "where can i edit", "files to edit", "modify the code", "where is", "where are", "location of", "defined in", "where defined")):
        return ChatIntent.WHERE_TO_EDIT
    if any(k in q for k in ("architecture", "architectural", "layers", "structure", "archetype", "entry point", "entrypoint", "state management", "visual effect", "effects", "context")):
        return ChatIntent.ARCHITECTURE
    if any(k in q for k in ("deep research", "complete analysis", "comprehensive", "files i would need")):
        return ChatIntent.RESEARCH
    if any(k in q for k in ("codemap", "request reaches", "trace", "flow to", "reach the database", "call graph", "how does", "explain how", "module")):
        if "trace" in q or "reach" in q or "flow" in q or "module" in q:
            return ChatIntent.CODEMAP_REQUEST
        if "change" in q or "impact" in q or "break" in q:
            return ChatIntent.CHANGE_IMPACT
        return ChatIntent.ARCHITECTURE
    if any(k in q for k in ("overview", "what is this repository", "what does this project do", "what does this repository do", "what does this application do", "what does this app do", "what does this codebase do", "summary", "getting started", "project does", "about")):
        return ChatIntent.OVERVIEW
    return ChatIntent.EXPLANATION