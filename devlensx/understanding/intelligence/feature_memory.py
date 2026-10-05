"""
DevLensX Feature Memory Subsystem (Phase 11.3)
Transforms AST & Graph data into evidence-grounded Feature Memory clusters.
Adapts dynamically to the codebase structure without forcing Controller->Service->Repository patterns.
"""

from typing import Dict, Any, List


class FeatureMemoryEngine:
    @staticmethod
    def extract_features(classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Groups codebase components into structured, traceable Feature Memory items."""
        prod_classes = [c for c in classes if not c.get("is_test") and not c["name"].endswith("Test") and not c["name"].endswith("Tests")]
        
        if not prod_classes:
            return [{
                "feature_id": "feat_empty",
                "name": "⚪ Empty / Unparsed Repository",
                "description": "No production source classes discovered in codebase.",
                "symbols": [],
                "files": [],
                "endpoints": [],
                "dependencies": [],
                "evidence": ["Repository Scanner"]
            }]

        # Cluster by package domain or module naming
        domain_clusters: Dict[str, List[Dict[str, Any]]] = {}
        for c in prod_classes:
            pkg = c.get("package", "") or ""
            parts = [p.capitalize() for p in pkg.split(".") if p not in ("com", "org", "net", "app", "model", "service", "controller", "repository", "entity")]
            
            domain = parts[-1] if parts else "Core Domain"
            if domain in ("Default", "Java", "Util", "Config"):
                domain = "System Configuration"

            if domain not in domain_clusters:
                domain_clusters[domain] = []
            domain_clusters[domain].append(c)

        features = []
        for idx, (domain_name, cls_list) in enumerate(domain_clusters.items(), 1):
            symbols = [c["name"] for c in cls_list]
            files = list(dict.fromkeys([c.get("file", "") for c in cls_list if c.get("file")]))
            
            # Aggregate REST endpoints discovered in this feature
            endpoints = []
            for c in cls_list:
                endpoints.extend(c.get("endpoints", []) or [])
            endpoints = list(dict.fromkeys(endpoints))

            # Aggregate dependencies
            deps = []
            for c in cls_list:
                deps.extend(c.get("injected_dependencies", []) or [])
            deps = list(dict.fromkeys([d for d in deps if d not in symbols]))

            features.append({
                "feature_id": f"feat_{domain_name.lower().replace(' ', '_')}_{idx}",
                "name": domain_name,
                "description": f"Domain capability encapsulating {len(symbols)} class symbol(s): {', '.join(symbols[:3])}.",
                "symbols": symbols,
                "files": files[:5],
                "endpoints": endpoints[:5],
                "dependencies": deps[:5],
                "evidence": ["AST Class Model", "Package Structure", "Dependency Graph"],
                "evidence_breakdown": {
                    "ast_parsed_classes": len(symbols),
                    "package_namespace": domain_name,
                    "graph_edges_count": len(deps),
                    "discovered_routes_count": len(endpoints),
                    "clustering_rationale": f"Grouped {len(symbols)} components based on shared package namespace and dependency graph references."
                }
            })

        return sorted(features, key=lambda f: len(f["symbols"]), reverse=True)
