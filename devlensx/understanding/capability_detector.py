"""
DevLensX Understanding Subsystem: Capability Detector
Discovers business capabilities (Accounts, Appointments, Orders, Payments, Notifications) without hardcoded layer assumptions.
Polyglot-aware: works with Java packages, Python modules, TypeScript namespaces, and any URM symbol.
"""

from typing import Dict, Any, List


class CapabilityDetector:
    @staticmethod
    def detect_capabilities(classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Groups codebase components into business capabilities based on package co-location and class names.
        
        Polyglot-aware: works with Java packages, Python module paths, TypeScript file paths,
        and any URMSymbol-derived class representation.
        """
        capabilities_map: Dict[str, List[str]] = {}

        for c in classes:
            name = c.get("name") or c.get("qualified_name", "")
            if not name:
                continue
            if c.get("is_test") or name.endswith("Test") or name.endswith("Tests") or name.endswith("Spec"):
                continue
            
            # Extract domain keyword from package, module path, or file path
            pkg = c.get("package", "") or c.get("module", "") or ""
            if not pkg:
                # Fallback: derive from file path directory
                file_path = c.get("file", "")
                if file_path:
                    parts = file_path.replace("\\", "/").split("/")
                    # Take the second-to-last segment (the containing directory)
                    pkg = parts[-2] if len(parts) >= 2 else ""

            # Strip common infrastructure namespaces and language-specific prefixes
            _SKIP_SEGMENTS = {
                "com", "org", "net", "app", "model", "service", "controller",
                "repository", "entity", "src", "main", "java", "kotlin", "python",
                "typescript", "javascript", "lib", "libs", "pkg", "packages",
                "internal", "impl", "base", "common", "util", "utils", "helper",
                "helpers", "shared", "core", "api", "domain", "__init__", "index",
            }
            parts = [
                p.capitalize()
                for p in pkg.replace("-", ".").replace("/", ".").split(".")
                if p and p not in _SKIP_SEGMENTS
            ]
            
            domain = parts[-1] if parts else "Core"
            if domain in ("Default", "Java", "Util", "Config", "Test", "Spec"):
                domain = "System Configuration"
                
            if domain not in capabilities_map:
                capabilities_map[domain] = []
            capabilities_map[domain].append(name)

        capabilities = []
        for domain_name, cls_list in capabilities_map.items():
            capabilities.append({
                "capability": domain_name,
                "components_count": len(cls_list),
                "components": cls_list[:8],
                "status": "🟢 DISCOVERED FROM AST STRUCTURE",
                "evidence_sources": cls_list[:3]
            })

        if not capabilities:
            all_names = [c.get("name") or c.get("qualified_name", "") for c in classes if c.get("name") or c.get("qualified_name")]
            capabilities.append({
                "capability": "Core Domain",
                "components_count": len(classes),
                "components": all_names[:5],
                "status": "🟢 DISCOVERED FROM REPOSITORY UNITS",
                "evidence_sources": all_names[:3]
            })

        return sorted(capabilities, key=lambda x: x["components_count"], reverse=True)

