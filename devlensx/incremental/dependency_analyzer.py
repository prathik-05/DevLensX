from typing import List, Dict, Any, Set

class DependencyAnalyzer:
    @staticmethod
    def find_affected_symbols(changed_symbols: List[str], graph_store=None, urm_classes: List[Dict[str, Any]] = None, max_hops: int = 3) -> Dict[str, List[str]]:
        """Find DIRECT, DOWNSTREAM, TEST, CONFIG affected symbols via Kuzu or fallback."""
        direct = list(changed_symbols)
        downstream: Set[str] = set()
        tests: Set[str] = set()
        configs: Set[str] = set()

        # Use Kuzu if available
        if graph_store and hasattr(graph_store, "query_change_impact"):
            for sym in changed_symbols:
                try:
                    impacted = graph_store.query_change_impact(sym) or []
                    for item in impacted:
                        name = item.get("class_name") or item.get("caller") or item.get("name")
                        if name and name not in direct:
                            downstream.add(name)
                        if item.get("is_test"):
                            tests.add(name)
                except Exception:
                    pass
        # Fallback via URM injected_dependencies
        if urm_classes:
            for c in urm_classes:
                deps = c.get("injected_dependencies") or []
                for changed in changed_symbols:
                    if changed in deps and c["name"] not in direct:
                        downstream.add(c["name"])
                    if c.get("is_test") or "Test" in c.get("name",""):
                        # Check if test relates to changed symbol
                        if changed.lower() in c["name"].lower():
                            tests.add(c["name"])
                # Config detection: crude
                if c.get("stereotype") == "Configuration" or "Config" in c.get("name",""):
                    for changed in changed_symbols:
                        if changed.lower() in c.get("file","").lower():
                            configs.add(c["name"])

        return {
            "DIRECT": direct,
            "DOWNSTREAM": sorted(downstream),
            "TEST": sorted(tests),
            "CONFIG": sorted(configs),
        }
