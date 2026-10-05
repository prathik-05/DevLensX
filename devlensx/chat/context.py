"""Context hierarchy — explicit priority P1 (selected source/symbol) to P6 (FAISS)."""

from typing import List, Dict, Any, Optional
from devlensx.chat.models import ChatContext


def build_context_query(context: Optional[ChatContext], user_message: str) -> str:
    """Prepends high-priority context signals to the retrieval query."""
    if not context:
        return user_message
    parts: List[str] = []
    # P1 selected source/symbol is highest priority
    if context.selected_symbol:
        parts.append(f"symbol:{context.selected_symbol}")
    if context.selected_file:
        parts.append(f"file:{context.selected_file}")
    if context.selected_node_id:
        parts.append(f"node:{context.selected_node_id}")
    if context.section_id:
        parts.append(f"section:{context.section_id}")
    if context.page_id:
        parts.append(f"page:{context.page_id}")
    parts.append(user_message)
    return " ".join(parts)


def describe_context(context: Optional[ChatContext]) -> Dict[str, Any]:
    if not context:
        return {"level": "repository", "priority": ["repo"]}
    level = "repository"
    if context.selected_file or context.selected_symbol:
        level = "source"
    elif context.selected_node_id:
        level = "diagram_node"
    elif context.section_id:
        level = "section"
    elif context.page_id:
        level = "page"
    return {"level": level, "priority": context.priority_summary()}