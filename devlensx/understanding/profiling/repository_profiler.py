"""
DevLensX Understanding Subsystem - Polyglot Repository Profiler
Analyzes real manifests, entrypoints, AST symbols, and configurations.

Enforces the frozen DevLensX trust contract:
1. Grounded Facts: Distinguishes OBSERVED / VERIFIED facts from INFERRED / SUGGESTION archetypes.
2. Polyglot Inspection: Inspects package.json, pom.xml, build.gradle, requirements.txt, pyproject.toml, Cargo.toml, go.mod.
3. Accurate Archetype Classification: FRONTEND_UI, WEB_BACKEND, CLI_ENGINE, FRAMEWORK_LIBRARY, DATA_ML_SYSTEM.
4. No Hardcoded Fallbacks: Never invents databases, frameworks, or controllers when unsupported by repository artifacts.
"""

from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set


class RepositoryProfiler:
    @staticmethod
    def profile_repository(repo_path: str, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Profiles repository identity, technology stack, entrypoints, and architectural archetype."""
        p = Path(repo_path)
        project_name = p.name or "Target Repository"

        # 1. Inspect real manifests on disk
        manifests_found: List[str] = []
        manifest_data: Dict[str, Any] = {}

        pom_path = p / "pom.xml"
        gradle_path = p / "build.gradle"
        pkg_json_path = p / "package.json"
        req_path = p / "requirements.txt"
        pyproject_path = p / "pyproject.toml"
        setup_path = p / "setup.py"
        cargo_path = p / "Cargo.toml"
        go_path = p / "go.mod"

        if pom_path.exists():
            manifests_found.append("pom.xml")
            try:
                manifest_data["pom"] = pom_path.read_text(encoding="utf-8", errors="ignore")[:5000]
            except Exception:
                pass

        if gradle_path.exists():
            manifests_found.append("build.gradle")

        if pkg_json_path.exists():
            manifests_found.append("package.json")
            try:
                manifest_data["package_json"] = json.loads(pkg_json_path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass

        if req_path.exists():
            manifests_found.append("requirements.txt")
            try:
                manifest_data["requirements"] = req_path.read_text(encoding="utf-8", errors="ignore")[:5000]
            except Exception:
                pass

        if pyproject_path.exists():
            manifests_found.append("pyproject.toml")

        if cargo_path.exists():
            manifests_found.append("Cargo.toml")

        if go_path.exists():
            manifests_found.append("go.mod")

        # 2. Determine Primary Language from AST file extensions + manifests
        file_paths = [str(c.get("file") or "").replace("\\", "/") for c in classes if c.get("file")]
        ext_counts: Dict[str, int] = {}
        for fp in file_paths:
            ext = Path(fp).suffix.lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        java_count = ext_counts.get(".java", 0)
        ts_count = ext_counts.get(".ts", 0) + ext_counts.get(".tsx", 0)
        js_count = ext_counts.get(".js", 0) + ext_counts.get(".jsx", 0)
        py_count = ext_counts.get(".py", 0)
        go_count = ext_counts.get(".go", 0)
        rs_count = ext_counts.get(".rs", 0)
        cpp_count = ext_counts.get(".cpp", 0) + ext_counts.get(".c", 0) + ext_counts.get(".h", 0)

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

        # 3. Detect Real Frameworks from manifests and AST annotations
        frameworks_detected: List[str] = []
        all_class_names = [str(c.get("name", "")).lower() for c in classes]
        all_text_blob = " ".join(all_class_names + file_paths).lower()

        # TypeScript / JS frameworks
        pkg = manifest_data.get("package_json", {})
        dependencies = {}
        if isinstance(pkg, dict):
            dependencies.update(pkg.get("dependencies", {}))
            dependencies.update(pkg.get("devDependencies", {}))

        dep_keys = {k.lower() for k in dependencies.keys()}

        if "react" in dep_keys or any(ext in ext_counts for ext in (".tsx", ".jsx")):
            frameworks_detected.append("React")
        if "next" in dep_keys:
            frameworks_detected.append("Next.js")
        if "vue" in dep_keys:
            frameworks_detected.append("Vue")
        if "express" in dep_keys:
            frameworks_detected.append("Express")
        if "vite" in dep_keys:
            frameworks_detected.append("Vite")

        # Python frameworks
        req_text = manifest_data.get("requirements", "").lower()
        if "fastapi" in req_text or "fastapi" in all_text_blob:
            frameworks_detected.append("FastAPI")
        if "flask" in req_text or "flask" in all_text_blob:
            frameworks_detected.append("Flask")
        if "django" in req_text or "django" in all_text_blob:
            frameworks_detected.append("Django")
        if "torch" in req_text or "pytorch" in req_text or "torch" in all_text_blob:
            frameworks_detected.append("PyTorch")
        if "ultralytics" in req_text or "yolo" in all_text_blob or "yolo" in req_text:
            frameworks_detected.append("YOLO / Computer Vision")
        if "opencv" in req_text or "cv2" in all_text_blob:
            frameworks_detected.append("OpenCV")

        # Java frameworks
        pom_text = manifest_data.get("pom", "").lower()
        if "spring-boot" in pom_text or any(c.get("stereotype") == "Controller" for c in classes) or "org.springframework" in all_text_blob:
            frameworks_detected.append("Spring Boot")
        if "mybatis" in pom_text or "mybatis" in all_text_blob:
            frameworks_detected.append("MyBatis")
        if "dubbo" in pom_text or "dubbo" in all_text_blob:
            frameworks_detected.append("Apache Dubbo")

        framework_str = " / ".join(frameworks_detected) if frameworks_detected else "Native / Modular Library"

        # 4. Detect Databases (Only if evidenced)
        databases: List[str] = []
        if "h2" in pom_text or any("h2" in fp.lower() for fp in file_paths):
            databases.append("H2 In-Memory DB")
        if "postgresql" in pom_text or "postgres" in req_text or "psycopg" in req_text:
            databases.append("PostgreSQL")
        if "mysql" in pom_text or "mysql" in req_text or any("mysql" in fp.lower() for fp in file_paths):
            databases.append("MySQL")
        if "sqlite" in req_text or any("sqlite" in fp.lower() for fp in file_paths):
            databases.append("SQLite")
        if "mongodb" in dep_keys or "mongoose" in dep_keys or "pymongo" in req_text:
            databases.append("MongoDB")
        if "redis" in dep_keys or "redis" in req_text:
            databases.append("Redis Cache")

        # 5. Discover Real Entrypoints from manifests and AST
        entry_points: List[Dict[str, str]] = []

        # Check main files
        for fp in file_paths:
            base_name = Path(fp).name.lower()
            if base_name in ("main.py", "app.py", "cli.py", "run.py", "index.ts", "index.tsx", "app.tsx", "main.tsx", "main.java", "application.java"):
                entry_points.append({"file": fp, "type": "Application Entrypoint"})

        # Check classes with entrypoint stereotypes or methods
        for c in classes:
            st = c.get("stereotype", "")
            c_name = c.get("name", "")
            if st == "Controller":
                entry_points.append({"symbol": c_name, "file": c.get("file", ""), "type": "HTTP Controller Ingress"})
            elif "application" in c_name.lower() and c.get("kind", "class") in ("class", "interface"):
                entry_points.append({"symbol": c_name, "file": c.get("file", ""), "type": "Application Bootstrapper"})

        # Deduplicate entrypoints
        seen_ep = set()
        unique_entrypoints = []
        for ep in entry_points:
            key = ep.get("symbol") or ep.get("file")
            if key and key not in seen_ep:
                seen_ep.add(key)
                unique_entrypoints.append(ep)

        # 6. Infer Architectural Archetype (strictly labeled as INFERRED / SUGGESTION)
        if any(f in frameworks_detected for f in ("React", "Next.js", "Vue", "Vite")) or            (primary_language in ("TypeScript", "JavaScript") and any(".tsx" in fp or ".jsx" in fp for fp in file_paths)):
            archetype = "FRONTEND_UI"
            archetype_rationale = f"Detected reactive UI components ({primary_language}) and web layout files."
        elif any(f in frameworks_detected for f in ("PyTorch", "YOLO / Computer Vision", "OpenCV")):
            archetype = "DATA_ML_SYSTEM"
            archetype_rationale = f"Detected machine learning / vision inference libraries ({', '.join(frameworks_detected)})."
        elif any(term in all_text_blob for term in ("battle", "ship", "game", "board", "cli", "command", "simulator", "calc")) and              not any(f in frameworks_detected for f in ("Spring Boot", "FastAPI", "Flask", "Django", "Express")):
            archetype = "CLI_ENGINE"
            archetype_rationale = f"Detected command/simulation loop patterns and algorithmic state structures in {primary_language}."
        elif any(f in frameworks_detected for f in ("MyBatis", "Apache Dubbo")) or "library" in project_name.lower():
            archetype = "FRAMEWORK_LIBRARY"
            archetype_rationale = f"Detected extensible framework middleware and builder patterns in {primary_language}."
        elif any(f in frameworks_detected for f in ("Spring Boot", "FastAPI", "Flask", "Django", "Express")) or any(c.get("stereotype") == "Controller" for c in classes):
            archetype = "WEB_BACKEND"
            archetype_rationale = f"Detected ingress routing controllers and service layer patterns in {primary_language}."
        else:
            archetype = "MODULAR_APPLICATION"
            archetype_rationale = f"Organized into modular structural units in {primary_language}."

        return {
            "project_name": project_name,
            "primary_language": primary_language,
            "manifests_found": manifests_found,
            "framework": framework_str,
            "frameworks_detected": frameworks_detected,
            "databases": databases if databases else ["None Explicitly Declared"],
            "entry_points": unique_entrypoints[:8],
            "archetype": archetype,
            "archetype_status": "INFERRED",
            "archetype_rationale": archetype_rationale,
            "total_parsed_units": len(classes),
            "identity_summary": (
                f"{primary_language} project ({framework_str}) with {len(classes)} parsed structural units. "
                f"Inferred structural archetype: {archetype}."
            )
        }
