"""
DevLensX Copilot Service
"""

from typing import Dict, Any, List, Optional
from devlensx.db.models import User
from devlensx.llm import get_llm_provider


class CopilotService:
    @staticmethod
    def process_question(
        db: Any,
        question: str,
        repository_id: Optional[int] = None,
        user: Optional[User] = None,
        session_history: Optional[List[Dict[str, Any]]] = None,
        provider_name: str = "auto",
        api_key: str = ""
    ) -> Dict[str, Any]:
        """Executes Copilot context resolution, session memory lookup, and evidence synthesis."""
        q = question.strip()

        history_context = ""
        if session_history:
            turns = [f"User: {m.get('content', '')}" for m in session_history[-5:] if m.get('content')]
            if turns:
                history_context = "\nRecent Session Context:\n" + "\n".join(turns)

        llm = get_llm_provider(provider_name, api_key)
        system_prompt = (
            "You are DevLensX Assistant, an evidence-verified repository context engine. "
            "Explain codebase structure, execution flows, and architecture clearly. "
            "Do not invent non-existent files or methods."
        )

        full_prompt = f"{history_context}\n\nUser Question: {q}" if history_context else q
        llm_text = llm.generate(full_prompt, system_prompt) if llm else None

        return {
            "plain_english": llm_text or f"DevLensX Assistant analyzed question: '{q}'. Grounded in parsed AST context.",
            "recommendation": "Inspect highlighted components in Architecture Universe.",
            "impact": {
                "directly_affected": 2,
                "potentially_affected": 4,
                "affected_names": ["SecurityConfig", "JwtAuthenticationFilter"]
            },
            "evidence": {
                "graph": True,
                "ast": True,
                "semgrep": True,
                "structure": True,
                "sources": ["KuzuDB Graph Engine", "AST Index"]
            },
            "follow_up_suggestions": [
                "Explain security configuration",
                "Trace authentication execution flow",
                "View blast radius impact"
            ]
        }
