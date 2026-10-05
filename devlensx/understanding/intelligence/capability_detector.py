"""
DevLensX Understanding - Intelligence Subsystem: Capability Detector
Discovers business capabilities with strict evidence verification and honest ambiguity reporting.
"""

from typing import Dict, Any, List


class CapabilityDetector:
    @staticmethod
    def detect_capabilities(classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Groups codebase components into business capabilities. Reports honest ambiguity if structure is small."""
        capabilities_map: Dict[str, List[str]] = {}

        prod_classes = [c for c in classes if not c.get("is_test") and not c["name"].endswith("Test")]

        for c in prod_classes:
            pkg = c.get("package", "") or ""
            parts = [p.capitalize() for p in pkg.split(".") if p not in ("com", "org", "net", "app", "model", "service", "controller", "repository", "entity")]
            
            domain = parts[-1] if parts else "Core"
            if domain in ("Default", "Java", "Util", "Config"):
                domain = "System Configuration"
                
            if domain not in capabilities_map:
                capabilities_map[domain] = []
            capabilities_map[domain].append(c["name"])

        capabilities = []
        for name, cls_list in capabilities_map.items():
            if len(cls_list) >= 2 or len(capabilities_map) == 1:
                capabilities.append({
                    "capability": name,
                    "components_count": len(cls_list),
                    "components": cls_list[:8],
                    "status": "🟢 DISCOVERED FROM AST STRUCTURE",
                    "evidence_sources": cls_list[:3]
                })

        # Honest Ambiguity Rule: Do not fabricate a "Core Domain" card if structure is small/ambiguous
        if not capabilities or len(prod_classes) <= 3:
            return [{
                "capability": "⚪ Repository Structure Ambiguous / Small",
                "components_count": len(prod_classes),
                "components": [c["name"] for c in prod_classes[:5]],
                "status": "⚪ AMBIGUOUS STRUCTURE",
                "note": f"DevLensX could not confidently identify distinct business capabilities. The repository contains {len(prod_classes)} primary source files.",
                "evidence_sources": [c["name"] for c in prod_classes[:3]]
            }]

        return sorted(capabilities, key=lambda x: x["components_count"], reverse=True)
