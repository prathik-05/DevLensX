"""
DevLensX Evidence-Grounded Diagram Generator
Generates machine-verifiable Mermaid diagrams directly from URM symbols and graph relationships.
"""

from typing import List, Dict, Any
from devlensx.urm.models import URMSymbol, URMRelationship


class EvidenceDiagramGenerator:
    @staticmethod
    def generate_architecture_diagram(symbols: List[URMSymbol], relationships: List[URMRelationship]) -> str:
        """Generates Mermaid flowchart string where nodes contain exact line provenance."""
        lines = ["graph TD"]
        sym_map = {s.id: s for s in symbols}

        # Select key types and controllers
        key_symbols = [s for s in symbols if s.stereotype in ("Controller", "Service", "Repository", "Component", "Context")]
        if not key_symbols:
            key_symbols = symbols[:10]

        for s in key_symbols:
            clean_name = s.name.replace("-", "_").replace(".", "_")
            label = f"{s.name} (L{s.line_start}-L{s.line_end})"
            lines.append(f'    {clean_name}["{label}"]')

        for r in relationships:
            src = sym_map.get(r.source_id)
            tgt = sym_map.get(r.target_id)
            if src and tgt and src in key_symbols and tgt in key_symbols:
                src_name = src.name.replace("-", "_").replace(".", "_")
                tgt_name = tgt.name.replace("-", "_").replace(".", "_")
                rel_label = r.relationship_type.value.lower()
                lines.append(f'    {src_name} -- "{rel_label}" --> {tgt_name}')

        return "\n".join(lines)
