"""
DevLensX Guided Code Map Generator
Builds interactive entrypoint guided tours and architectural code maps linking nodes to documentation & line provenance.
"""

from typing import List, Dict, Any
from devlensx.urm.models import UniversalRepositoryModel, URMSymbol


class CodeMapGenerator:
    @staticmethod
    def generate_code_map(urm: UniversalRepositoryModel) -> Dict[str, Any]:
        """Builds a structured step-by-step entrypoint tour of the repository."""
        entrypoints = [s for s in urm.symbols if s.stereotype in ("Controller", "Component", "Context", "RouteHandler") or "main" in s.name.lower() or "app" in s.name.lower()]
        if not entrypoints and urm.symbols:
            entrypoints = urm.symbols[:3]

        steps = []
        for idx, ep in enumerate(entrypoints[:5], 1):
            deps = [r.target_id for r in urm.relationships if r.source_id == ep.id]
            steps.append({
                "step": idx,
                "node_id": ep.id,
                "name": ep.name,
                "kind": ep.kind.value,
                "stereotype": ep.stereotype or "Module",
                "file": ep.file,
                "citation": f"{ep.file}#L{ep.line_start}-{ep.line_end}",
                "dependencies_count": len(deps),
                "description": f"Entrypoint module {ep.name} managing primary business interaction."
            })

        return {
            "repository": urm.name,
            "total_tour_steps": len(steps),
            "tour_steps": steps
        }
