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
        seen_god = set()
        from devlensx.understanding.profiling.repository_profiler import is_test_file_or_symbol

        for c in repo_model.get("classes", []):
            if not isinstance(c, dict) or not c.get("name"):
                continue
            name = c["name"]
            if name in seen_god:
                continue

            file_path = c.get("file", "")
            # Exclude test fixtures and test cases from architectural God Class alerts
            if is_test_file_or_symbol(file_path, name) or c.get("is_test"):
                continue

            fp_lower = file_path.replace("\\", "/").lower()
            # Cohesive domain models, entities, DTOs, and value objects represent data/state, not god classes
            is_model_or_pojo = (
                any(seg in fp_lower for seg in ("/model/", "/entity/", "/domain/", "/dto/", "/vo/")) or
                c.get("stereotype") in ("Model", "Entity", "DTO", "VO", "POJO", "Config", "Configuration") or
                name.endswith(("DTO", "Model", "Config", "Entity", "Event"))
            )

            n_methods = len(prod_methods(_method_index, name)) if _method_index \
                else len(c.get("methods", []) or [])

            deps_count = len(c.get("injected_dependencies", []) or [])
            fields_count = len(c.get("fields", []) or [])
            loc = c.get("loc") or max(0, (c.get("line_end", 0) or 0) - (c.get("line_start", 0) or 0))

            # Explainable structural God Class heuristic:
            # 1. Models/entities must have extreme method bloat (>35 methods) and high coupling to be god classes
            # 2. General classes require >15 methods AND structural complexity indicators (coupling, fields, or high LOC)
            is_god_class = False
            if is_model_or_pojo:
                if n_methods > 35 and fields_count > 15 and deps_count >= 3:
                    is_god_class = True
            else:
                if n_methods > 15 and (deps_count >= 2 or fields_count >= 6 or loc >= 250 or n_methods >= 25):
                    is_god_class = True

            if is_god_class:
                seen_god.add(name)
                god_classes.append({
                    "class_name": name,
                    "file": file_path,
                    "method_count": n_methods,
                    "stereotype": c.get("stereotype", ""),
                    "deps_count": deps_count,
                    "fields_count": fields_count,
                    "loc": loc,
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

        deduped_findings = []
        seen_f = set()
        for f in findings:
            key = (f.get("category"), f.get("title"), f.get("class_name"), f.get("file"))
            if key not in seen_f:
                seen_f.add(key)
                deduped_findings.append(f)

        return {
            "layer_flows": layer_flows,
            "dependency_chains": dependency_chains,
            "god_classes": god_classes,
            "findings": deduped_findings
        }
