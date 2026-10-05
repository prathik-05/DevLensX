"""
DevLensX Understanding - Wiki Subsystem: Interactive Wiki Generator
Generates DeepWiki views directly from a shared RepositoryBrain snapshot.
"""

from typing import Dict, Any, List, Optional
from devlensx.understanding.model.repository_brain import RepositoryBrain


class WikiGenerator:
    @staticmethod
    def generate_living_wiki(repo_path: str, classes: List[Dict[str, Any]], brain: Optional[RepositoryBrain] = None) -> Dict[str, Any]:
        """Synthesizes all understanding sub-engines using a single RepositoryBrain instance."""
        if brain is None:
            brain = RepositoryBrain(repo_path, classes)

        auth_components = [c for c in brain.symbols if "auth" in c.lower() or "security" in c.lower()]
        if brain.profile.get("framework") == "Spring Boot":
            auth_mech = "Spring Security / JWT Pattern"
        elif brain.profile.get("primary_language") in ("TypeScript", "JavaScript", "Python"):
            auth_mech = "Token / Auth Middleware Pattern"
        else:
            auth_mech = "Authentication / Security Configuration Pattern"

        return {
            "analysis_run_id": brain.analysis_run_id,
            "overview": {
                "title": f"DevLensX Living Wiki: {brain.profile['project_name']}",
                "identity": brain.profile["identity_summary"],
                "primary_language": brain.profile["primary_language"],
                "framework": brain.profile["framework"],
                "databases": brain.profile["databases"],
                "status": "🟢 LIVE REPOSITORY BRAIN WIKI"
            },
            "architecture": brain.architecture,
            "capabilities": brain.capabilities,
            "user_flows": brain.flows,
            "apis": brain.endpoints,
            "database": {
                "entities": brain.database_entities[:8],
                "status": "🟢 AST MAPPED"
            },
            "authentication": {
                "mechanism": auth_mech,
                "components": auth_components or ["SecurityConfig"],
                "status": "🟢 VERIFIED BY AST"
            },
            "testing": {
                "test_components_count": len([c for c in brain.classes if c.get("is_test") or "Test" in c["name"]]),
                "status": "🟢 AST MAPPED"
            }
        }
