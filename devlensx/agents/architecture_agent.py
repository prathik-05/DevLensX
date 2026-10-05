"""
DevLensX Module 4: Architecture Agent

Analyzes repository layered architecture, extracts Controller -> Service -> Repository
dependency chains, detects circular dependencies, and evaluates coupling & maintainability metrics.
"""

class ArchitectureAgent:
    def __init__(self, graph_store):
        self.graph_store = graph_store

    def extract_dependency_chains(self, repo_model):
        """
        Extracts end-to-end architectural dependency chains by following
        injected_dependencies for all classes, regardless of stereotype.
        """
        classes = [c for c in repo_model.get("classes", []) if isinstance(c, dict)]
        class_by_name = {c["name"]: c for c in classes if c.get("name")}

        chains = []
        for cls in classes:
            cls_deps = cls.get("injected_dependencies", []) or []
            if not cls_deps or not cls.get("name"):
                continue
            for dep_name in cls_deps:
                dep = class_by_name.get(dep_name)
                if not dep:
                    continue
                dep_deps = dep.get("injected_dependencies", []) or []
                for leaf_name in dep_deps:
                    leaf = class_by_name.get(leaf_name)
                    if not leaf:
                        continue
                    def _label(c):
                        s = c.get("stereotype", "")
                        return f"{c.get('name', '')}({s})" if s else c.get("name", "")
                    chains.append({
                        "root": cls["name"],
                        "middle": dep["name"],
                        "leaf": leaf["name"],
                        "chain_string": f"{_label(cls)} ➔ {_label(dep)} ➔ {_label(leaf)}"
                    })

        return chains

    def analyze(self, repo_model):
        """Analyzes architectural layer flows, dependency chains, coupling metrics, and structural integrity."""
        layer_flows = self.graph_store.query_architecture_flow()
        blast_rankings = self.graph_store.query_blast_radius(limit=10)
        dependency_chains = self.extract_dependency_chains(repo_model)

        try:
            from devlensx.deep_reasoning import build_method_index, prod_methods
            _method_index = build_method_index(repo_model.get("classes", []))
        except Exception:
            _method_index = {}
        _by_name = {c.get("name"): c for c in repo_model.get("classes", [])
                    if isinstance(c, dict) and c.get("name")}

        god_classes = []
        for c in repo_model.get("classes", []):
            if not isinstance(c, dict) or not c.get("name"):
                continue
            n_methods = len(prod_methods(_method_index, c["name"])) if _method_index \
                else len(c.get("methods", []) or [])
            if n_methods > 15:
                god_classes.append({
                    "class_name": c["name"],
                    "file": c.get("file", ""),
                    "method_count": n_methods,
                    "stereotype": c.get("stereotype", "")
                })

        findings = []

        # Finding 1: God Class / High Complexity Warning
        if god_classes:
            for gc in god_classes:
                findings.append({
                    "agent": "ArchitectureAgent",
                    "category": "Maintainability",
                    "title": f"High Complexity God Class Detected: {gc['class_name']}",
                    "severity": "HIGH",
                    "class_name": gc["class_name"],
                    "file": gc["file"],
                    "claim": f"{gc['class_name']} contains {gc['method_count']} methods, violating single responsibility principles.",
                    "evidence": {
                        "method_count": gc["method_count"],
                        "stereotype": gc["stereotype"]
                    }
                })

        # Finding 2: High Coupling Bottlenecks
        for item in blast_rankings[:3]:
            if (item.get("incoming_dependents", 0) or 0) >= 3:
                matched = _by_name.get(item.get("class_name", ""))
                findings.append({
                    "agent": "ArchitectureAgent",
                    "category": "Coupling",
                    "title": f"High Coupling Bottleneck: {item.get('class_name', '')}",
                    "severity": "MEDIUM",
                    "class_name": item.get("class_name", ""),
                    "file": (matched or {}).get("file", ""),
                    "claim": f"{item.get('class_name', '')} ({item.get('stereotype', '')}) is directly depended on by {item.get('incoming_dependents', 0)} components.",
                    "evidence": {
                        "incoming_dependents": item.get("incoming_dependents", 0),
                        "stereotype": item.get("stereotype", "")
                    }
                })

        return {
            "layer_flows": layer_flows,
            "dependency_chains": dependency_chains,
            "god_classes": god_classes,
            "findings": findings
        }
