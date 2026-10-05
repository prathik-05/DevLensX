"""Research planner for Deep Research mode — subquestion generation."""

from typing import List


RESEARCH_TEMPLATES = [
    "Where is {topic} configured?",
    "Which endpoints and handlers involve {topic}?",
    "What middleware or interceptors participate in {topic}?",
    "Which classes and symbols implement {topic}?",
    "What persistence or data layer is used for {topic}?",
    "What files would need to change to modify {topic}?",
]


def plan_research(user_query: str, max_subquestions: int = 6) -> List[str]:
    q = user_query.strip() or "repository architecture"
    # Extract a topic phrase: use first noun-like chunk or full query
    topic = q.split("?")[0].strip().lower()
    # keep it short for template filling
    if len(topic) > 40:
        topic = topic[:40].rsplit(" ", 1)[0]
    subquestions = []
    for tmpl in RESEARCH_TEMPLATES[:max_subquestions]:
        subquestions.append(tmpl.format(topic=topic))
    return subquestions