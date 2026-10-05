"""
DevLensX Module 1: Repository Parser Package
Polyglot parsing using Tree-sitter and language adapters.
"""

from devlensx.shared.types import (
    TreeSitterParser,
    get_treesitter_parser,
    ParseResult,
    SupportedLanguage,
    detect_language,
)
from devlensx.urm.models import UniversalRepositoryModel, URMSymbol, URMRelationship, URMEndpoint, URMConfiguration, URMFramework

from typing import List, Dict, Any, Optional
from pathlib import Path
import time


def _get_adapter_registry():
    """Lazy import to avoid circular dependency."""
    from devlensx.urm.adapters import get_initialized_registry
    return get_initialized_registry()


def parse_repo(repo_path: str) -> Dict[str, Any]:
    """
    Parse an entire repository using Tree-sitter and language adapters.
    Returns a Universal Repository Model compatible dictionary.
    """
    start_time = time.time()
    
    parser = get_treesitter_parser()
    registry = _get_adapter_registry()
    
    # Parse all files in repository
    parse_results = parser.parse_repository(repo_path)
    
    # Process through adapters
    all_symbols: List[URMSymbol] = []
    all_relationships: List[URMRelationship] = []
    all_endpoints: List[URMEndpoint] = []
    all_configurations: List[URMConfiguration] = []
    all_frameworks: List[URMFramework] = []
    parse_errors: List[Dict[str, Any]] = []
    
    files_parsed = 0
    files_failed = 0
    files_skipped = 0
    language_stats: Dict[str, int] = {}
    
    for result in parse_results:
        if not result.success:
            files_failed += 1
            parse_errors.append({
                "file": result.file_path,
                "error": "; ".join(result.parse_errors),
                "language": result.language.value if result.language else "unknown",
            })
            continue
        
        # Process through appropriate adapter via the registry
        adapter = registry.get(result.language)
        if not adapter:
            # Config-only languages (json/yaml/toml) without adapters are skipped, not errors
            files_skipped += 1
            continue
        
        files_parsed += 1
        language_stats[result.language.value] = language_stats.get(result.language.value, 0) + 1
        
        try:
            processed = registry.process_parse_result(result)
            
            all_symbols.extend(processed["symbols"])
            all_relationships.extend(processed["relationships"])
            all_endpoints.extend(processed["endpoints"])
            all_configurations.extend(processed["configurations"])
            all_frameworks.extend(processed["frameworks"])
        except Exception as e:
            parse_errors.append({
                "file": result.file_path,
                "error": f"Adapter processing failed: {str(e)}",
                "language": result.language.value,
            })
    
    # Build Universal Repository Model
    repo_name = Path(repo_path).name
    primary_language = max(language_stats, key=language_stats.get) if language_stats else "Unknown"
    
    # Calculate language percentages
    total_files = sum(language_stats.values())
    languages_pct = {lang: (count / total_files * 100) for lang, count in language_stats.items()} if total_files > 0 else {}
    
    urm = UniversalRepositoryModel(
        repository_id=repo_name,
        name=repo_name,
        root_path=repo_path,
        primary_language=primary_language,
        languages=languages_pct,
        frameworks=_deduplicate_frameworks(all_frameworks),
        symbols=all_symbols,
        relationships=all_relationships,
        endpoints=all_endpoints,
        configurations=all_configurations,
    )
    
    # Convert to legacy dictionary format for backward compatibility
    legacy_dict = _urm_to_legacy_dict(urm, repo_path, parse_errors, files_parsed, files_failed, time.time() - start_time)
    
    return legacy_dict


def _deduplicate_frameworks(frameworks: List[URMFramework]) -> List[URMFramework]:
    """Deduplicate frameworks by name and language."""
    seen = set()
    unique = []
    for f in frameworks:
        key = (f.name, f.language)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _relativize(file_path: str, repo_path: str) -> str:
    """Converts an absolute/repo-prefixed path to a repo-relative POSIX path."""
    if not file_path:
        return ""
    p = file_path.replace("\\", "/")
    try:
        rel = str(Path(p).resolve().relative_to(Path(repo_path).resolve()))
        return rel.replace("\\", "/")
    except Exception:
        pass
    try:
        rel = Path(p).relative_to(Path(repo_path))
        return str(rel).replace("\\", "/")
    except Exception:
        pass
    # Heuristic fallback: strip everything up to and including the repo folder
    repo_folder = Path(repo_path).name
    parts = p.split("/")
    if repo_folder in parts:
        return "/".join(parts[parts.index(repo_folder) + 1:])
    return p


def _urm_to_legacy_dict(urm: UniversalRepositoryModel, repo_path: str,
                        parse_errors: List[Dict], files_parsed: int, 
                        files_failed: int, parse_time: float) -> Dict[str, Any]:
    """Convert URM to legacy dictionary format for backward compatibility."""
    repo_name = Path(repo_path).name
    
    # Convert symbols to legacy class format.
    # Complete the legacy schema from data the adapters already emit:
    # injected/extends/implements from URM relationships, fields by source
    # range containment, is_test from stereotype/path — so downstream
    # consumers (critic, agents, graph) see populated keys, not missing ones.
    def _file_of(sym):
        try:
            return _relativize(sym.location.file_path, repo_path)
        except Exception:
            return ""

    classes = []
    for symbol in urm.symbols:
        if symbol.kind.name in ("CLASS", "STRUCT", "INTERFACE", "ENUM", "TRAIT",
                                "FUNCTION", "METHOD", "CONSTRUCTOR"):
            meta = dict(symbol.metadata or {})

            def _str_list(v):
                if isinstance(v, list):
                    return [str(x) for x in v if x]
                if v:
                    return [str(v)]
                return []

            cls = {
                "name": symbol.name,
                "qualified_name": symbol.qualified_name,
                "kind": symbol.kind.value.lower() if hasattr(symbol.kind, 'value') else str(symbol.kind).lower(),
                "stereotype": symbol.stereotype or "Class",
                "file": _file_of(symbol),
                "package": _extract_package(symbol.qualified_name),
                "line_start": symbol.location.start_line,
                "line_end": symbol.location.end_line,
                "language": symbol.language,
                "signature": symbol.signature,
                "annotations": list(symbol.annotations or []),
                "modifiers": list(symbol.modifiers or []),
                "is_static": bool(symbol.is_static),
                "is_async": bool(symbol.is_async),
                "generics": list(symbol.generics or []),
                "metadata": meta,
                "fields": [],
                "injected_dependencies": _str_list(meta.get("injected_dependencies")),
                "extends": _str_list(meta.get("extends")),
                "implements": _str_list(meta.get("implements")),
                "file_imports": _str_list(meta.get("file_imports")),
                "is_test": bool((symbol.stereotype or "") == "Test"),
            }
            classes.append(cls)

    by_id = {}
    for s in urm.symbols:
        try:
            by_id[s.id] = s
        except Exception:
            pass
    by_name = {}
    for cls in classes:
        by_name.setdefault(cls["name"], cls)

    def _simple(rid):
        s = str(rid or "")
        import re as _re
        m = _re.match(r"^([a-z]{2,10})_(.+?)_(\d+)$", s)
        if m and m.group(2)[:1].isupper():
            return m.group(2).split(".")[-1]
        return s.split(".")[-1]

    # FIELD symbols attach to their enclosing class by file + line range.
    field_syms = [s for s in urm.symbols
                  if getattr(s.kind, "name", "") == "FIELD"]
    for fsym in field_syms:
        try:
            ffile = _file_of(fsym)
            fl, fe = fsym.location.start_line, fsym.location.end_line
        except Exception:
            continue
        for cls in classes:
            if cls["file"] != ffile or cls["kind"] not in ("class", "interface", "struct", "enum"):
                continue
            cs, ce = cls.get("line_start") or 0, cls.get("line_end") or 0
            if cs and ce and cs <= (fl or 0) and (fe or 0) <= ce:
                cls["fields"].append({
                    "name": fsym.name,
                    "type": (fsym.metadata or {}).get("type", ""),
                    "annotations": list(fsym.annotations or []),
                })
                break

    # Relationships complete injected/extends/implements/file_imports.
    for r in urm.relationships:
        try:
            rtype = r.relationship_type.value.upper() if hasattr(r.relationship_type, "value") else str(r.relationship_type).upper()
        except Exception:
            continue
        src = by_name.get(_simple(getattr(r, "source_id", "")))
        tgt = _simple(getattr(r, "target_id", ""))
        if not src or not tgt:
            continue
        if rtype in ("DEPENDS_ON", "DEPENDENCY", "INJECTS", "CALLS", "USES", "REFERENCES"):
            if tgt not in src["injected_dependencies"]:
                src["injected_dependencies"].append(tgt)
        elif rtype in ("EXTENDS", "INHERITS"):
            if tgt not in src["extends"]:
                src["extends"].append(tgt)
        elif rtype in ("IMPLEMENTS",):
            if tgt not in src["implements"]:
                src["implements"].append(tgt)
        elif rtype in ("IMPORTS",):
            imp = getattr(r, "target_id", "")
            if imp and imp not in src["file_imports"]:
                src["file_imports"].append(imp)

    # is_test from path conventions as well as stereotype.
    for cls in classes:
        f = (cls.get("file") or "").replace("\\", "/").lower()
        if "/test/" in f or "/tests/" in f or f.startswith("test/"):
            cls["is_test"] = True
    
    # Legacy statistics
    stereotype_counts = {}
    for cls in classes:
        st = cls.get("stereotype", "Other")
        stereotype_counts[st] = stereotype_counts.get(st, 0) + 1
    
    total_endpoints = len(urm.endpoints)
    total_methods = len([c for c in classes if c.get("kind") in ("method", "function")])
    total_injected = len([c for c in classes if c.get("metadata", {}).get("injected_dependencies")])
    
    # Build system detection
    build_system = "Unknown"
    repo_root = Path(repo_path)
    if (repo_root / "pom.xml").exists():
        build_system = "Maven"
    elif (repo_root / "build.gradle").exists() or (repo_root / "build.gradle.kts").exists():
        build_system = "Gradle"
    elif (repo_root / "package.json").exists():
        build_system = "npm"
    elif (repo_root / "requirements.txt").exists() or (repo_root / "pyproject.toml").exists():
        build_system = "pip"
    elif (repo_root / "go.mod").exists():
        build_system = "Go Modules"
    elif (repo_root / "Cargo.toml").exists():
        build_system = "Cargo"
    elif (repo_root / "CMakeLists.txt").exists():
        build_system = "CMake"
    elif next(repo_root.glob("*.csproj"), None) is not None:
        build_system = "MSBuild"
    
    repo_summary = {
        "repository": repo_name,
        "language": urm.primary_language,
        "framework": urm.frameworks[0].name if urm.frameworks else "",
        "repo_type": f"{urm.primary_language} Repository",
        "analysis_scope": "Full Repository",
        "has_java_capability": "java" in [s.language for s in urm.symbols],
        "build_system": build_system,
        "language_profile": {
            "java_files": sum(1 for s in urm.symbols if s.language == "java"),
            "python_files": sum(1 for s in urm.symbols if s.language == "python"),
            "typescript_files": sum(1 for s in urm.symbols if s.language == "typescript"),
            "javascript_files": sum(1 for s in urm.symbols if s.language == "javascript"),
            "go_files": sum(1 for s in urm.symbols if s.language == "go"),
            "rust_files": sum(1 for s in urm.symbols if s.language == "rust"),
            "csharp_files": sum(1 for s in urm.symbols if s.language == "csharp"),
            "cpp_files": sum(1 for s in urm.symbols if s.language == "cpp"),
            "build_system": build_system,
        },
        "controllers": stereotype_counts.get("Controller", 0),
        "services": stereotype_counts.get("Service", 0),
        "repositories": stereotype_counts.get("Repository", 0),
        "entities": stereotype_counts.get("Entity", 0) + stereotype_counts.get("Model", 0),
        "rest_apis": total_endpoints,
        "total_classes": len(classes),
        "total_injected_dependencies": total_injected,
    }
    
    return {
        "repo": repo_name,
        "repo_summary": repo_summary,
        "stats": {
            "files_parsed": files_parsed,
            "files_failed": files_failed,
            "classes_found": len(classes),
            "methods_found": total_methods,
            "endpoints_found": total_endpoints,
            "stereotypes": stereotype_counts,
            "has_java_capability": "java" in [s.language for s in urm.symbols],
            "repo_type": f"{urm.primary_language} Repository",
            "build_system": build_system,
        },
        "classes": classes,
        "parse_errors": parse_errors,
        "endpoints": [{"route": e.route, "method": e.http_method, "handler": e.handler_symbol_id,
                       "framework": e.framework, "file": _relativize(e.location.file_path, repo_path)} for e in urm.endpoints],
        "configurations": [{"file": _relativize(c.file_path, repo_path), "key": c.key, "value": c.value} for c in urm.configurations],
        "frameworks": [{"name": f.name, "language": f.language, "version": f.version} for f in urm.frameworks],
        "relationships": [{"source": r.source_id, "target": r.target_id, "type": r.relationship_type.value} for r in urm.relationships],
    }


def _extract_package(qualified_name: str) -> str:
    """Extract package/namespace from qualified name."""
    parts = qualified_name.split(".")
    if len(parts) > 1:
        return ".".join(parts[:-1])
    parts = qualified_name.split("::")
    if len(parts) > 1:
        return "::".join(parts[:-1])
    return ""


# Keep backward compatibility
def parse_file(filepath, repo_root):
    """Legacy single file parse - not used in new pipeline."""
    parser = get_treesitter_parser()
    result = parser.parse_file(filepath)
    if result.success:
        registry = _get_adapter_registry()
        adapter = registry.get(result.language)
        if adapter:
            return adapter.process_parse_result(result)
    return {"symbols": [], "relationships": [], "endpoints": [], "configurations": [], "frameworks": []}


# Export main functions
__all__ = ["parse_repo", "parse_file", "ParseResult", "SupportedLanguage"]