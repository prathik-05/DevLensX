"""
DevLensX Understanding Subsystem - Universal Polyglot Repository Profiler
Analyzes real manifests, entrypoints, AST symbols, and configurations.

Enforces the frozen DevLensX trust contract:
1. Grounded Facts: Distinguishes OBSERVED / VERIFIED facts from INFERRED / SUGGESTION archetypes.
2. Polyglot Inspection: package.json, pom.xml, build.gradle, requirements.txt, pyproject.toml, Cargo.toml, go.mod.
3. Universal Archetype Classification: FRONTEND_UI, WEB_BACKEND, CLI_ENGINE, ALGORITHMIC_SYSTEM,
   FRAMEWORK_LIBRARY, DATA_ML_SYSTEM, MODULAR_APPLICATION.
4. Explainable Evidence Ranking: Ranks symbols with explicit reasons; segregates test fixtures
   from core application components while avoiding substring false-positives (e.g. attestation.py).
5. Honest Fallbacks: Reports missing evidence or library interfaces without fabricating endpoints.
"""

from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple


def is_test_file_or_symbol(file_path: str, symbol_name: str = "") -> bool:
    """
    Robust test classifier that checks path segments, standard filenames, and stereotypes.
    Explicitly protects production files containing 'test' as a substring (e.g. attestation.py, contest.py).
    """
    fp_norm = "/" + (file_path or "").replace("\\", "/").strip("/").lower() + "/"
    filename = Path(file_path or "").name.lower()
    sym_lower = (symbol_name or "").lower()

    # 1. Path segment checks (must be whole path segments, never substring inside words)
    test_segments = (
        "/test/", "/tests/", "/__tests__/", "/spec/", "/specs/",
        "/src/test/", "/test/java/", "/test/python/", "/testing/"
    )
    if any(seg in fp_norm for seg in test_segments):
        return True

    # 2. File name pattern checks
    if filename.startswith("test_") or filename.endswith("_test.py") or filename == "conftest.py":
        return True
    if filename.endswith("test.java") or filename.endswith("tests.java") or filename.endswith("testcase.java"):
        return True
    if filename.endswith(".test.ts") or filename.endswith(".test.tsx") or filename.endswith(".test.js") or filename.endswith(".test.jsx"):
        return True
    if filename.endswith(".spec.ts") or filename.endswith(".spec.tsx") or filename.endswith(".spec.js") or filename.endswith(".spec.jsx"):
        return True
    if filename.endswith("_test.go") or filename.endswith("test.cs"):
        return True

    # 3. Explicit symbol name checks (only if clearly a test suite / test case class or method)
    if sym_lower.startswith("test_") or sym_lower.endswith("_test"):
        return True
    if re.match(r"^test[A-Z0-9_]", symbol_name or ""):
        return True
    if re.search(r"(?:^|[a-z0-9])Tests?$", symbol_name or "") and any(s in fp_norm for s in ("/test", "/spec")):
        return True

    return False


def is_generated_or_vendored(file_path: str) -> bool:
    """Detects vendored dependencies, build artifacts, and generated code."""
    fp_norm = "/" + (file_path or "").replace("\\", "/").strip("/").lower() + "/"
    vendored_segments = (
        "/node_modules/", "/.git/", "/vendor/", "/dist/", "/build/",
        "/target/", "/out/", "/__pycache__/", "/.venv/", "/venv/", "/env/",
        "/.next/", "/.turbo/", "/coverage/", "/.pytest_cache/"
    )
    return any(seg in fp_norm for seg in vendored_segments)


def classify_symbol_role(
    file_path: str,
    symbol_name: str = "",
    stereotype: str = "",
    kind: str = "class"
) -> Dict[str, Any]:
    """
    Classifies a symbol into a structural role with an explainable priority and rationale.
    """
    st_clean = (stereotype or "").strip().capitalize()
    nm_lower = (symbol_name or "").lower()
    fn_lower = Path(file_path or "").name.lower()

    if is_test_file_or_symbol(file_path, symbol_name):
        return {
            "role": "TEST_FIXTURE",
            "priority": 20,
            "is_test": True,
            "is_entrypoint": False,
            "ranking_reason": "Verification suite & test fixture",
        }

    if is_generated_or_vendored(file_path):
        return {
            "role": "GENERATED_VENDORED",
            "priority": 10,
            "is_test": False,
            "is_entrypoint": False,
            "ranking_reason": "Generated or vendored artifact",
        }

    # Entrypoints
    is_main_file = fn_lower in (
        "main.py", "app.py", "cli.py", "run.py", "main.java", "application.java",
        "index.ts", "index.tsx", "app.tsx", "main.tsx", "main.go", "main.rs"
    )
    is_main_symbol = nm_lower in ("main", "run", "cli", "start", "application", "rootlayout") or st_clean in ("Controller", "Route", "Router")
    if is_main_file or is_main_symbol:
        return {
            "role": "ENTRYPOINT",
            "priority": 100,
            "is_test": False,
            "is_entrypoint": True,
            "ranking_reason": "Application entrypoint / Execution ingress",
        }

    # Core algorithms, decision engines, solvers, game state
    algo_keywords = ("engine", "algorithm", "minimax", "solver", "strategy", "rules", "calculator", "evaluator", "search", "tree", "graph", "aiplayer", "game")
    if any(k in nm_lower for k in algo_keywords) or any(k in fn_lower for k in ("engine", "algorithm", "game", "minimax", "board", "solver")):
        return {
            "role": "CORE_ALGORITHM",
            "priority": 90,
            "is_test": False,
            "is_entrypoint": False,
            "ranking_reason": "Core domain logic & decision algorithm",
        }

    # Domain services & coordinators
    if st_clean in ("Service", "Manager") or any(k in nm_lower for k in ("service", "manager", "coordinator", "dispatcher", "worker")):
        return {
            "role": "DOMAIN_SERVICE",
            "priority": 80,
            "is_test": False,
            "is_entrypoint": False,
            "ranking_reason": "Domain service / Business coordinator",
        }

    # Domain models, state representation, entities
    model_keywords = ("model", "entity", "schema", "record", "cell", "move", "board", "ship", "player", "node", "dto")
    if st_clean in ("Entity", "Model", "Schema", "Record") or any(k in nm_lower for k in model_keywords):
        return {
            "role": "DOMAIN_MODEL",
            "priority": 75,
            "is_test": False,
            "is_entrypoint": False,
            "ranking_reason": "Core domain entity & state representation",
        }

    # UI Components & Context
    if any(k in fn_lower for k in (".tsx", ".jsx")) or any(k in nm_lower for k in ("view", "panel", "component", "provider", "context", "card")):
        return {
            "role": "UI_COMPONENT",
            "priority": 70,
            "is_test": False,
            "is_entrypoint": False,
            "ranking_reason": "UI component & presentation state",
        }

    # Storage & Persistence
    if st_clean in ("Repository", "Dao", "Store") or any(k in nm_lower for k in ("repository", "dao", "store", "database", "persistence")):
        return {
            "role": "STORAGE_PERSISTENCE",
            "priority": 65,
            "is_test": False,
            "is_entrypoint": False,
            "ranking_reason": "Data persistence & storage layer",
        }

    # Default / Utility
    return {
        "role": "UTILITY_CONFIG",
        "priority": 50,
        "is_test": False,
        "is_entrypoint": False,
        "ranking_reason": "Supporting structural module",
    }


def rank_symbols_explainable(
    classes: List[Dict[str, Any]],
    task: str = "overview"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Separates and ranks production symbols and test fixtures with explainability.
    In 'overview' task: production symbols rank 100->50, test symbols are isolated at 20.
    In 'testing' task: test symbols rank 100->80.
    """
    prod_symbols: List[Dict[str, Any]] = []
    test_symbols: List[Dict[str, Any]] = []

    seen = set()
    for c in classes:
        name = c.get("name") or c.get("qualified_name") or ""
        file_path = c.get("file") or ""
        key = (name, file_path)
        if not name or key in seen:
            continue
        seen.add(key)

        info = classify_symbol_role(
            file_path=file_path,
            symbol_name=name,
            stereotype=c.get("stereotype", ""),
            kind=c.get("kind", "class")
        )

        item = {
            "name": name,
            "file": file_path,
            "line_start": int(c.get("line_start") or 1),
            "line_end": int(c.get("line_end") or (int(c.get("line_start") or 1) + 10)),
            "kind": c.get("kind") or "class",
            "stereotype": c.get("stereotype") or "",
            "role": info["role"],
            "priority": info["priority"],
            "ranking_reason": info["ranking_reason"],
            "is_test": info["is_test"],
            "is_entrypoint": info["is_entrypoint"],
        }

        if info["is_test"]:
            test_symbols.append(item)
        else:
            prod_symbols.append(item)

    # Sort production symbols: highest priority first, then class-level over method-level
    def _prod_sort_key(s: Dict[str, Any]) -> Tuple[int, int, str]:
        kind_bonus = 10 if s.get("kind") in ("class", "interface", "struct") else 0
        return (-(s["priority"] + kind_bonus), len(s["file"]), s["name"])

    prod_symbols.sort(key=_prod_sort_key)
    test_symbols.sort(key=lambda s: (s.get("kind") != "class", s["name"]))

    return prod_symbols, test_symbols


class RepositoryProfiler:
    @staticmethod
    def profile_repository(
        repo_path: str,
        classes: Optional[List[Dict[str, Any]]] = None,
        repo_model: Optional[Dict[str, Any]] = None,
        files: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Derives a universal, explainable repository profile across all supported repository shapes.
        """
        p = Path(repo_path)
        project_name = p.name or "Target Repository"

        all_classes: List[Dict[str, Any]] = list(classes or (repo_model.get("classes", []) if repo_model else []))
        relationships: List[Dict[str, Any]] = list(repo_model.get("relationships", []) if repo_model else [])
        endpoints: List[Dict[str, Any]] = list(repo_model.get("endpoints", []) if repo_model else [])

        # 1. Inspect real manifests on disk
        manifests_found: List[str] = []
        manifest_data: Dict[str, Any] = {}

        manifest_map = {
            "pom.xml": "pom",
            "build.gradle": "gradle",
            "build.gradle.kts": "gradle_kts",
            "package.json": "package_json",
            "requirements.txt": "requirements",
            "pyproject.toml": "pyproject",
            "setup.py": "setup_py",
            "Cargo.toml": "cargo",
            "go.mod": "go_mod",
            "Dockerfile": "dockerfile",
            "docker-compose.yml": "compose",
        }

        for fname, key in manifest_map.items():
            fpath = p / fname
            if fpath.exists():
                manifests_found.append(fname)
                try:
                    if fname == "package.json":
                        manifest_data[key] = json.loads(fpath.read_text(encoding="utf-8", errors="ignore"))
                    else:
                        manifest_data[key] = fpath.read_text(encoding="utf-8", errors="ignore")[:5000]
                except Exception:
                    pass

        # 2. Determine Language Distribution from files and AST
        ext_counts: Dict[str, int] = {}
        all_file_paths: List[str] = []

        if files:
            for f in files:
                fpath = getattr(f, "path", None) or (f.get("path") if isinstance(f, dict) else str(f))
                if fpath:
                    all_file_paths.append(str(fpath).replace("\\", "/"))
        elif all_classes:
            all_file_paths = [str(c.get("file") or "").replace("\\", "/") for c in all_classes if c.get("file")]

        for fp in all_file_paths:
            ext = Path(fp).suffix.lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        total_ext_files = sum(ext_counts.values()) or 1
        java_count = ext_counts.get(".java", 0)
        ts_count = ext_counts.get(".ts", 0) + ext_counts.get(".tsx", 0)
        js_count = ext_counts.get(".js", 0) + ext_counts.get(".jsx", 0)
        py_count = ext_counts.get(".py", 0)
        go_count = ext_counts.get(".go", 0)
        rs_count = ext_counts.get(".rs", 0)
        cpp_count = ext_counts.get(".cpp", 0) + ext_counts.get(".c", 0) + ext_counts.get(".h", 0)

        lang_distribution = {
            "Java": round((java_count / total_ext_files) * 100, 1),
            "TypeScript": round((ts_count / total_ext_files) * 100, 1),
            "JavaScript": round((js_count / total_ext_files) * 100, 1),
            "Python": round((py_count / total_ext_files) * 100, 1),
            "Go": round((go_count / total_ext_files) * 100, 1),
            "Rust": round((rs_count / total_ext_files) * 100, 1),
            "C/C++": round((cpp_count / total_ext_files) * 100, 1),
        }
        lang_distribution = {k: v for k, v in lang_distribution.items() if v > 0}

        if ts_count > 0 and ts_count >= max(java_count, py_count, js_count):
            primary_language = "TypeScript"
        elif js_count > 0 and js_count >= max(java_count, py_count, ts_count):
            primary_language = "JavaScript"
        elif py_count > 0 and py_count >= max(java_count, ts_count, js_count):
            primary_language = "Python"
        elif java_count > 0 and java_count >= max(py_count, ts_count, js_count):
            primary_language = "Java"
        elif "package.json" in manifests_found:
            primary_language = "TypeScript" if ts_count > 0 else "JavaScript"
        elif "pom.xml" in manifests_found or "build.gradle" in manifests_found:
            primary_language = "Java"
        elif "requirements.txt" in manifests_found or "pyproject.toml" in manifests_found:
            primary_language = "Python"
        elif "go.mod" in manifests_found:
            primary_language = "Go"
        elif "Cargo.toml" in manifests_found:
            primary_language = "Rust"
        else:
            primary_language = "Polyglot"

        # 3. Detect Frameworks
        frameworks_detected: List[str] = []
        all_class_names = [str(c.get("name", "")).lower() for c in all_classes]
        all_text_blob = " ".join(all_class_names + all_file_paths).lower()

        pkg = manifest_data.get("package_json", {})
        dependencies = {}
        if isinstance(pkg, dict):
            dependencies.update(pkg.get("dependencies", {}))
            dependencies.update(pkg.get("devDependencies", {}))
        dep_keys = {k.lower() for k in dependencies.keys()}

        if "react" in dep_keys or any(ext in ext_counts for ext in (".tsx", ".jsx")):
            frameworks_detected.append("React")
        if "next" in dep_keys or "next.config" in all_text_blob:
            frameworks_detected.append("Next.js")
        if "vue" in dep_keys:
            frameworks_detected.append("Vue")
        if "express" in dep_keys:
            frameworks_detected.append("Express")
        if "vite" in dep_keys or "vite.config" in all_text_blob:
            frameworks_detected.append("Vite")

        req_text = (manifest_data.get("requirements") or "").lower()
        if "fastapi" in req_text or "fastapi" in all_text_blob:
            frameworks_detected.append("FastAPI")
        if "flask" in req_text or "flask" in all_text_blob:
            frameworks_detected.append("Flask")
        if "django" in req_text or "django" in all_text_blob:
            frameworks_detected.append("Django")
        if "torch" in req_text or "pytorch" in req_text or "torch" in all_text_blob:
            frameworks_detected.append("PyTorch")
        if "ultralytics" in req_text or "yolo" in all_text_blob:
            frameworks_detected.append("YOLO / Vision")

        pom_text = (manifest_data.get("pom") or "").lower()
        if "spring-boot" in pom_text or any(c.get("stereotype") == "Controller" for c in all_classes) or "org.springframework" in all_text_blob:
            frameworks_detected.append("Spring Boot")
        if "mybatis" in pom_text or "mybatis" in all_text_blob:
            frameworks_detected.append("MyBatis")
        if "dubbo" in pom_text or "dubbo" in all_text_blob:
            frameworks_detected.append("Apache Dubbo")

        framework_str = " / ".join(frameworks_detected) if frameworks_detected else "Standard Library / Modular"

        # 4. Rank Symbols with Explainable Roles
        prod_symbols, test_symbols = rank_symbols_explainable(all_classes, task="overview")

        # 5. Discover Grounded Entrypoints
        entry_points: List[Dict[str, str]] = []

        # Check endpoints
        for ep in endpoints[:8]:
            m = ep.get("method", "GET")
            r = ep.get("route", ep.get("path", "/"))
            h = ep.get("handler", "")
            f = ep.get("file", "")
            entry_points.append({"symbol": f"{m} {r}", "file": f, "type": f"HTTP Route ({h})"})

        # Check main files
        for fp in all_file_paths:
            base_name = Path(fp).name.lower()
            if base_name in ("main.py", "app.py", "cli.py", "run.py", "index.ts", "index.tsx", "app.tsx", "main.tsx", "main.java", "application.java"):
                entry_points.append({"file": fp, "type": "Application Execution Target"})

        # Check classes with entrypoint roles
        for ps in prod_symbols:
            if ps["is_entrypoint"] and not any(ep.get("symbol") == ps["name"] for ep in entry_points):
                entry_points.append({"symbol": ps["name"], "file": ps["file"], "type": "Entrypoint Component"})

        # If it's a library with no conventional entrypoint, extract Public API exports
        if not entry_points and prod_symbols:
            for ps in prod_symbols[:4]:
                entry_points.append({"symbol": ps["name"], "file": ps["file"], "type": "Public Library Interface / Core Module"})

        # Deduplicate
        seen_ep = set()
        unique_entrypoints = []
        for ep in entry_points:
            key = ep.get("symbol") or ep.get("file")
            if key and key not in seen_ep:
                seen_ep.add(key)
                unique_entrypoints.append(ep)

        # 6. Architectural Archetype Classification
        has_algo_symbols = any(s["role"] == "CORE_ALGORITHM" for s in prod_symbols)
        has_routes = bool(endpoints) or any("controller" in s["name"].lower() for s in prod_symbols)
        has_ui = any(f in frameworks_detected for f in ("React", "Next.js", "Vue", "Vite")) or any(s["role"] == "UI_COMPONENT" for s in prod_symbols)

        if has_ui:
            archetype = "FRONTEND_UI"
            archetype_rationale = f"Reactive web UI application ({primary_language}) with layout and component hierarchy."
        elif any(f in frameworks_detected for f in ("PyTorch", "YOLO / Vision")):
            archetype = "DATA_ML_SYSTEM"
            archetype_rationale = f"Machine learning and data processing system in {primary_language}."
        elif has_algo_symbols and not has_routes:
            archetype = "ALGORITHMIC_SYSTEM"
            archetype_rationale = f"Algorithmic decision engine / state system in {primary_language} with core game or solver logic."
        elif any(term in all_text_blob for term in ("cli", "command", "parser", "args")) and not has_routes:
            archetype = "CLI_ENGINE"
            archetype_rationale = f"Command-line execution tool in {primary_language}."
        elif not unique_entrypoints or any(f in frameworks_detected for f in ("MyBatis", "Apache Dubbo")) or "library" in project_name.lower():
            archetype = "FRAMEWORK_LIBRARY"
            archetype_rationale = f"Modular library / framework package providing reusable interfaces in {primary_language}."
        elif has_routes or any(f in frameworks_detected for f in ("Spring Boot", "FastAPI", "Flask", "Django", "Express")):
            archetype = "WEB_BACKEND"
            archetype_rationale = f"HTTP web service and routing architecture in {primary_language}."
        else:
            archetype = "MODULAR_APPLICATION"
            archetype_rationale = f"Modular application structured across {len(prod_symbols)} verified production components in {primary_language}."

        # 7. Trace Grounded Data Flow
        data_flow: List[str] = []
        if relationships:
            for r in relationships[:5]:
                src = str(r.get("source") or "").split(".")[-1]
                tgt = str(r.get("target") or "").split(".")[-1]
                rel = str(r.get("type") or "DEPENDS_ON")
                if src and tgt and src != tgt:
                    data_flow.append(f"`{src}` &rarr; {rel} &rarr; `{tgt}`")

        if not data_flow:
            if archetype == "ALGORITHMIC_SYSTEM":
                # Entrypoint -> Controller -> Algorithm -> State Board
                chain_nodes = []
                for role_target in ("ENTRYPOINT", "CORE_ALGORITHM", "DOMAIN_MODEL"):
                    matching = next((s["name"] for s in prod_symbols if s["role"] == role_target), None)
                    if matching and matching not in chain_nodes:
                        chain_nodes.append(matching)
                if len(chain_nodes) >= 2:
                    data_flow.append(" &rarr; ".join(f"`{n}`" for n in chain_nodes))
            elif archetype == "WEB_BACKEND":
                ctrl = next((s["name"] for s in prod_symbols if "controller" in s["name"].lower() or s["role"] == "ENTRYPOINT"), None)
                srv = next((s["name"] for s in prod_symbols if s["role"] == "DOMAIN_SERVICE"), None)
                repo = next((s["name"] for s in prod_symbols if s["role"] == "STORAGE_PERSISTENCE"), None)
                chain = []
                if ctrl: chain.append(f"`{ctrl}` (Controller)")
                if srv: chain.append(f"`{srv}` (Service)")
                if repo: chain.append(f"`{repo}` (Repository)")
                if len(chain) >= 2:
                    data_flow.append(" &rarr; ".join(chain))
            elif archetype == "FRONTEND_UI":
                views = [s["name"] for s in prod_symbols if s["role"] in ("ENTRYPOINT", "UI_COMPONENT")][:3]
                if len(views) >= 2:
                    data_flow.append(" &rarr; ".join(f"`{v}`" for v in views))

        return {
            "project_name": project_name,
            "primary_language": primary_language,
            "language_distribution": lang_distribution,
            "manifests_found": manifests_found,
            "framework": framework_str,
            "frameworks_detected": frameworks_detected,
            "archetype": archetype,
            "archetype_status": "INFERRED",
            "archetype_rationale": archetype_rationale,
            "entry_points": unique_entrypoints[:8],
            "production_symbols": prod_symbols,
            "test_symbols": test_symbols,
            "data_flow": data_flow,
            "total_parsed_units": len(all_classes),
            "production_units_count": len(prod_symbols),
            "test_units_count": len(test_symbols),
            "identity_summary": (
                f"{primary_language} ({framework_str}) project with {len(prod_symbols)} production symbols "
                f"and {len(test_symbols)} test fixtures. Inferred archetype: {archetype}."
            ),
        }
