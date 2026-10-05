"""
DevLensX - Module 1: Repository Intelligence Parser (Java AST via javalang)

Parses Java/Spring Boot repositories to extract AST entities:
  - Classes & Interfaces (Package, Annotations, Extends, Implements)
  - Stereotype Classification (Controller, Service, Repository, Entity, Component, Config, Test)
  - Fields & Constructors (handling @Autowired, @Resource, @Inject, and Lombok @RequiredArgsConstructor)
  - REST Endpoints (merging class-level base path with method-level annotations)
  - Imports for Qualified Name (qname) edge resolution
"""

import javalang
import json
import re
import sys
from pathlib import Path

ENDPOINT_ANNOTATIONS = {
    "RequestMapping", "GetMapping", "PostMapping", "PutMapping",
    "DeleteMapping", "PatchMapping"
}

STEREOTYPE_ANNOTATIONS = {
    "RestController": "Controller",
    "Controller": "Controller",
    "Service": "Service",
    "Repository": "Repository",
    "Component": "Component",
    "Entity": "Entity",
    "Configuration": "Configuration",
    "Bean": "Component"
}


def parse_generic_file(filepath, repo_root):
    """Fallback AST regex parser for Python, JS/TS, Go, C#, C/C++ files."""
    try:
        rel_path = filepath.relative_to(repo_root).as_posix()
    except Exception:
        rel_path = str(filepath).replace("\\", "/")

    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            with open(str(filepath), "r", encoding="latin-1", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

    ext = filepath.suffix.lower()
    filename = filepath.stem

    classes = []
    # Enhanced regex matching class/interface/type/struct/record/trait/enum declarations across languages
    class_pattern = re.compile(
        r"(?:export\s+(?:default\s+)?)?"
        r"(?:public|protected|private|sealed|abstract)?\s*"
        r"(?:class|interface|type|struct|record|trait|enum|module)\s+"
        r"([A-Za-z0-9_]+)",
        re.MULTILINE
    )
    class_matches = class_pattern.findall(content)

    # Enhanced method pattern: python def, js/ts function/arrow, go func, C#/Java/Rust methods
    method_pattern = re.compile(
        r"(?:def|function|func|fn|public|private|protected|async\s+def|async\s+function)\s+"
        r"(?:\([^\)]*\)\s*)?"
        r"([A-Za-z0-9_]+)\s*\(",
        re.MULTILINE
    )
    method_matches = method_pattern.findall(content)

    arrow_pattern = re.compile(
        r"(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
        re.MULTILINE
    )
    method_matches.extend(arrow_pattern.findall(content))
    method_matches = list(dict.fromkeys(method_matches))

    stereotype = "Other"
    fn_lower = filename.lower()
    if "controller" in fn_lower or "router" in fn_lower or "api" in fn_lower or "views" in fn_lower:
        stereotype = "Controller"
    elif "service" in fn_lower or "handler" in fn_lower or "manager" in fn_lower:
        stereotype = "Service"
    elif "repository" in fn_lower or "db" in fn_lower or "dao" in fn_lower or "models" in fn_lower:
        stereotype = "Repository"
    elif "entity" in fn_lower or "model" in fn_lower or "schema" in fn_lower:
        stereotype = "Entity"
    elif "test" in fn_lower or "spec" in fn_lower:
        stereotype = "Test"

    inferred_classes = class_matches if class_matches else [filename.capitalize()]

    try:
        pkg_name = str(filepath.parent.relative_to(repo_root)).replace("/", ".")
    except Exception:
        pkg_name = str(filepath.parent).replace("/", ".")

    for cls_name in inferred_classes:
        methods = [{"name": m, "return_type": "void", "annotations": [], "line_number": 1} for m in method_matches[:10]]
        classes.append({
            "name": cls_name,
            "qname": f"{rel_path}:{cls_name}",
            "stereotype": stereotype,
            "kind": "class",
            "file": rel_path,
            "package": pkg_name,
            "annotations": ["Controller" if stereotype == "Controller" else stereotype],
            "extends": None,
            "implements": [],
            "injected_dependencies": [],
            "fields": [],
            "methods": methods,
            "endpoints": [{"http_method": "GET", "path": f"/{filename.lower()}", "full_path": f"/{filename.lower()}", "method_name": m["name"]} for m in methods if stereotype == "Controller"],
            "is_test": stereotype == "Test"
        })

    return classes


def annotation_name(ann):
    return getattr(ann, "name", str(ann))


def _clean(v):
    if isinstance(v, str):
        return v.strip('"')
    return str(v) if v is not None else ""


def clean_type_name(raw):
    """Extracts inner type from generic wrappers like List<Owner> -> Owner, Optional<Pet> -> Pet cleanly."""
    if not raw:
        return ""
    clean = str(raw).strip()
    clean = re.sub(r'@[A-Za-z0-9_]+', '', clean).strip()
    clean = clean.replace("[]", "").strip()
    while "<" in clean and ">" in clean:
        try:
            start = clean.index("<")
            end = clean.rindex(">")
            inner = clean[start + 1:end].strip()
            if "," in inner:
                inner = inner.split(",")[-1].strip()
            clean = inner
        except Exception:
            break
    if "." in clean:
        clean = clean.split(".")[-1].strip()
    return clean


def annotation_value(ann):
    """Extract path/value string from annotation element."""
    if ann.element is None:
        return None
    el = ann.element
    if hasattr(el, "value"):
        val = getattr(el, "value", None)
        if hasattr(val, "value"):
            return _clean(val.value)
        return _clean(val)
    if isinstance(el, list):
        for pair in el:
            if getattr(pair, "name", None) in ("value", "path") and hasattr(pair, "value"):
                v = pair.value
                if hasattr(v, "value"):
                    return _clean(v.value)
                return _clean(v)
    return None


def combine_paths(base_path, method_path):
    """Combines class-level base path and method-level path cleanly."""
    base = (base_path or "").rstrip("/")
    sub = (method_path or "").lstrip("/")
    if not base and not sub:
        return "/"
    if not base:
        return "/" + sub
    if not sub:
        return base
    return f"{base}/{sub}"


def extract_type(node, kind, package, is_test=False):
    class_annotations_raw = node.annotations or []
    class_annotations = [annotation_name(a) for a in class_annotations_raw]

    # Line position extraction
    line_start = node.position.line if hasattr(node, "position") and node.position else 1

    # Stereotype detection via Annotation + Class Suffix fallback
    stereotype = "Other"
    if is_test or node.name.endswith("Test") or node.name.endswith("Tests"):
        stereotype = "Test"
    else:
        for ann in class_annotations:
            if ann in STEREOTYPE_ANNOTATIONS:
                stereotype = STEREOTYPE_ANNOTATIONS[ann]
                break

    # Suffix fallback for Spring Data repositories, MyBatis mappers, RPC services
    if stereotype == "Other":
        n_lower = node.name.lower()
        if "controller" in n_lower or "resource" in n_lower:
            stereotype = "Controller"
        elif "service" in n_lower:
            stereotype = "Service"
        elif "repository" in n_lower or "dao" in n_lower or "mapper" in n_lower:
            stereotype = "Repository"
        elif "entity" in n_lower or "model" in n_lower or "dto" in n_lower:
            stereotype = "Entity"
        elif "config" in n_lower or "configuration" in n_lower:
            stereotype = "Configuration"

    # Class-level RequestMapping base path
    class_base_path = None
    for a in class_annotations_raw:
        if annotation_name(a) in ("RequestMapping", "GetMapping"):
            class_base_path = annotation_value(a)
            break

    # Lombok DI detection (@RequiredArgsConstructor / @AllArgsConstructor)
    has_lombok_di = any(a in ("RequiredArgsConstructor", "AllArgsConstructor") for a in class_annotations)

    fields = []
    field_injected = []
    for f in getattr(node, "fields", []) or []:
        f_annotations = [annotation_name(a) for a in (f.annotations or [])]
        f_type = f.type.name if hasattr(f.type, "name") else str(f.type)
        is_autowired = any(a in ("Autowired", "Resource", "Inject") for a in f_annotations)
        is_final = "final" in (f.modifiers or set())

        for decl in f.declarators:
            fields.append({
                "name": decl.name,
                "type": f_type,
                "annotations": f_annotations,
                "is_injected": is_autowired,
                "is_final": is_final
            })
            if is_autowired or (has_lombok_di and is_final):
                field_injected.append(f_type)

    methods = []
    endpoints = []
    for m in getattr(node, "methods", []) or []:
        m_annotations_raw = m.annotations or []
        m_annotations = [annotation_name(a) for a in m_annotations_raw]
        params = []
        for p in m.parameters:
            p_type = p.type.name if hasattr(p.type, "name") else str(p.type)
            params.append({"name": p.name, "type": p_type})
        ret_type = m.return_type.name if (m.return_type and hasattr(m.return_type, "name")) else "void"

        m_line = m.position.line if hasattr(m, "position") and m.position else line_start
        method_entry = {
            "name": m.name,
            "annotations": m_annotations,
            "params": params,
            "return_type": ret_type,
            "line_number": m_line,
            "line_range": f"{m_line}-{m_line + 15}"
        }
        methods.append(method_entry)

        endpoint_anns = [a for a in m_annotations_raw if annotation_name(a) in ENDPOINT_ANNOTATIONS]
        for a in endpoint_anns:
            method_path = annotation_value(a) or ""
            full_path = combine_paths(class_base_path, method_path)
            endpoints.append({
                "method_name": m.name,
                "http_annotation": annotation_name(a),
                "path": full_path,
            })

    raw_extends = getattr(node, "extends", None)
    if raw_extends is None:
        extends_list = []
    elif isinstance(raw_extends, list):
        extends_list = [str(e.name) for e in raw_extends]
    else:
        extends_list = [str(raw_extends.name)]

    # Constructor injection
    constructor_injected = []
    for ctor in getattr(node, "constructors", []) or []:
        for p in ctor.parameters:
            p_type = p.type.name if hasattr(p.type, "name") else str(p.type)
            constructor_injected.append(p_type)

    all_injected = list(dict.fromkeys(field_injected + constructor_injected))

    return {
        "name": node.name,
        "kind": kind,
        "package": package,
        "stereotype": stereotype,
        "annotations": class_annotations,
        "extends": extends_list,
        "implements": [str(i.name) for i in (getattr(node, "implements", None) or [])],
        "fields": fields,
        "methods": methods,
        "endpoints": endpoints,
        "injected_dependencies": all_injected,
        "line_start": line_start,
        "line_range": f"{line_start}-{line_start + len(methods) * 15 + 10}"
    }


def parse_file_fallback(filepath, repo_root, src):
    """Regex-assisted fallback parser for modern Java 17/21 features (records, sealed classes)."""
    try:
        rel_path = str(Path(filepath).relative_to(repo_root))
    except Exception:
        rel_path = str(filepath)

    pkg_match = re.search(r'package\s+([\w\.]+);', src)
    package = pkg_match.group(1) if pkg_match else ""
    imports = re.findall(r'import\s+([\w\.\*]+);', src)
    is_test = "src/test/" in rel_path.replace("\\", "/")

    class_match = re.search(r'(?:public|protected|private)?\s*(?:abstract|final|sealed)?\s*(class|interface|enum|record)\s+(\w+)', src)
    if not class_match:
        return None

    kind = class_match.group(1)
    cname = class_match.group(2)

    stereotype = "Other"
    if is_test or cname.endswith("Test") or cname.endswith("Tests"):
        stereotype = "Test"
    elif "@RestController" in src or "@Controller" in src or "controller" in cname.lower() or "resource" in cname.lower():
        stereotype = "Controller"
    elif "@Service" in src or "service" in cname.lower():
        stereotype = "Service"
    elif "@Repository" in src or "repository" in cname.lower() or "dao" in cname.lower() or "mapper" in cname.lower():
        stereotype = "Repository"
    elif "@Entity" in src or "entity" in cname.lower() or "model" in cname.lower():
        stereotype = "Entity"
    elif "@Configuration" in src or "config" in cname.lower():
        stereotype = "Configuration"

    extends_match = re.search(r'extends\s+([\w\<\>\,\s]+?)(?:implements|\{|\n)', src)
    extends_list = [clean_type_name(e.strip()) for e in extends_match.group(1).split(',')] if extends_match else []

    impl_match = re.search(r'implements\s+([\w\<\>\,\s]+?)(?:\{|\n)', src)
    impl_list = [clean_type_name(i.strip()) for i in impl_match.group(1).split(',')] if impl_match else []

    method_matches = re.findall(r'(?:public|protected|private)\s+([\w\<\>]+)\s+(\w+)\s*\(([^\)]*)\)', src)
    methods = []
    for m in method_matches:
        methods.append({
            "name": m[1],
            "annotations": [],
            "params": [],
            "return_type": clean_type_name(m[0])
        })

    injected = re.findall(r'@(?:Autowired|Resource|Inject)\s+(?:private|protected|public)?\s*([\w\<\>]+)', src)
    final_fields = re.findall(r'private\s+final\s+([\w\<\>]+)', src)
    all_injected = list(dict.fromkeys([clean_type_name(i) for i in (injected + final_fields) if clean_type_name(i)]))

    return {
        "file": rel_path,
        "package": package,
        "imports": imports,
        "is_test": is_test,
        "classes": [{
            "name": cname,
            "kind": kind,
            "package": package,
            "stereotype": stereotype,
            "annotations": [],
            "extends": extends_list,
            "implements": impl_list,
            "fields": [],
            "methods": methods,
            "endpoints": [],
            "injected_dependencies": all_injected,
        }]
    }


def parse_file(filepath, repo_root):
    src = None
    try:
        p_path = Path(filepath)
        p_str = str(p_path.resolve())
        if sys.platform == "win32" and not p_str.startswith("\\\\?\\") and not p_str.startswith("\\\\"):
            p_str = "\\\\?\\" + p_str
        with open(p_str, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
    except Exception:
        try:
            with open(str(filepath), "r", encoding="utf-8", errors="ignore") as f:
                src = f.read()
        except Exception as e:
            return None, f"FILE_OPEN_ERROR: {e}"

    if src is None:
        return None, "FILE_READ_EMPTY"

    try:
        tree = javalang.parse.parse(src)
    except Exception:
        # Robust AST Fallback for modern Java 17/21 features (records, sealed classes, text blocks)
        fb_parsed = parse_file_fallback(filepath, repo_root, src)
        if fb_parsed:
            return fb_parsed, None
        return None, "PARSE_ERROR"

    try:
        rel_path = str(Path(filepath).relative_to(repo_root)).replace("\\", "/")
    except Exception:
        rel_path = str(filepath).replace("\\", "/")

    package = tree.package.name if tree.package else ""
    imports = [imp.path for imp in (tree.imports or [])]
    is_test = "src/test/" in rel_path.lower()

    file_result = {
        "file": rel_path,
        "package": package,
        "imports": imports,
        "is_test": is_test,
        "classes": []
    }

    for path, node in tree.filter(javalang.tree.ClassDeclaration):
        file_result["classes"].append(extract_type(node, "class", package, is_test))
    for path, node in tree.filter(javalang.tree.InterfaceDeclaration):
        file_result["classes"].append(extract_type(node, "interface", package, is_test))

    return file_result, None


KNOWN_REPOS = {
    "spring-petclinic": "https://github.com/spring-projects/spring-petclinic.git",
    "mybatis-3": "https://github.com/mybatis/mybatis-3.git",
    "dubbo": "https://github.com/apache/dubbo.git"
}


def parse_repo(repo_path):
    repo_input = str(repo_path).strip()
    target_dir = Path(repo_input)

    # Auto-clone if Git URL, GitHub owner/repo, or known target repo name
    if not target_dir.exists():
        url_to_clone = None
        clean_input = repo_input.strip().rstrip("/")
        
        if clean_input.startswith("http://") or clean_input.startswith("https://") or clean_input.endswith(".git"):
            url_to_clone = clean_input
            repo_name = Path(clean_input).stem.replace(".git", "")
            target_dir = Path("eval_repos") / repo_name
        elif clean_input.lower() in KNOWN_REPOS:
            url_to_clone = KNOWN_REPOS[clean_input.lower()]
            target_dir = Path("eval_repos") / clean_input.lower()
        elif clean_input.lower().replace("eval_repos/", "") in KNOWN_REPOS:
            short_name = clean_input.lower().replace("eval_repos/", "")
            url_to_clone = KNOWN_REPOS[short_name]
            target_dir = Path("eval_repos") / short_name
        elif "/" in clean_input and not clean_input.startswith("/") and not clean_input.startswith("\\") and ":" not in clean_input:
            url_to_clone = f"https://github.com/{clean_input}.git"
            repo_name = clean_input.split("/")[-1].replace(".git", "")
            target_dir = Path("eval_repos") / repo_name

        if url_to_clone:
            if not target_dir.exists():
                print(f"[+] Auto-cloning target repository from {url_to_clone} into {target_dir}...")
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                try:
                    import git
                    git.Repo.clone_from(url_to_clone, target_dir, depth=1)
                    print(f"[+] Successfully cloned {target_dir.name} via GitPython.")
                except Exception:
                    import subprocess
                    print(f"[+] Falling back to native git CLI clone for {url_to_clone}...")
                    subprocess.run(["git", "clone", "--depth", "1", url_to_clone, str(target_dir)], check=True)
                    print(f"[+] Successfully cloned {target_dir.name} via git CLI.")

    repo_root = target_dir.resolve()
    java_files = list(repo_root.rglob("*.java"))
    results = []
    errors = []

    for jf in java_files:
        parsed, err = parse_file(jf, repo_root)
        if err:
            try:
                rel_err_f = str(jf.relative_to(repo_root)).replace("\\", "/")
            except Exception:
                rel_err_f = str(jf).replace("\\", "/")
            errors.append({"file": rel_err_f, "error": err})
        else:
            results.append(parsed)

    all_classes = []
    for file_result in results:
        for c in file_result["classes"]:
            c["file"] = file_result["file"]
            c["file_imports"] = file_result["imports"]
            c["is_test"] = file_result["is_test"]
            all_classes.append(c)

    stereotype_counts = {}
    for c in all_classes:
        st = c["stereotype"]
        stereotype_counts[st] = stereotype_counts.get(st, 0) + 1

    total_endpoints = sum(len(c["endpoints"]) for c in all_classes)
    total_methods = sum(len(c["methods"]) for c in all_classes)
    total_injected = sum(len(c["injected_dependencies"]) for c in all_classes)

    # Build System Detection
    build_system = "Direct Source Tree"
    if (repo_root / "pom.xml").exists():
        build_system = "Maven"
    elif (repo_root / "build.gradle").exists() or (repo_root / "build.gradle.kts").exists():
        build_system = "Gradle"
    elif (repo_root / "settings.gradle").exists() or (repo_root / "settings.gradle.kts").exists():
        build_system = "Gradle (Multi-Module)"

    py_count = len(list(repo_root.rglob("*.py")))
    js_ts_count = len(list(repo_root.rglob("*.js"))) + len(list(repo_root.rglob("*.ts")))
    cpp_count = len(list(repo_root.rglob("*.cpp"))) + len(list(repo_root.rglob("*.c")))
    java_count = len(results)

    has_java_capability = java_count > 0

    if not has_java_capability:
        repo_type = "Non-Java"
        analysis_scope = "Universal Multi-Language Analysis"
        # Parse non-Java files using generic fallback parser
        for non_java_ext in ("*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.go", "*.cs"):
            for f in repo_root.rglob(non_java_ext):
                if any(ignored in f.parts for ignored in ["node_modules", "venv", ".git", "dist", "build", "__pycache__"]):
                    continue
                try:
                    parsed_cls = parse_generic_file(f, repo_root)
                    for c in parsed_cls:
                        all_classes.append(c)
                        st = c["stereotype"]
                        stereotype_counts[st] = stereotype_counts.get(st, 0) + 1
                        total_methods += len(c["methods"])
                        total_endpoints += len(c["endpoints"])
                except Exception:
                    pass

        if py_count >= js_ts_count and py_count >= cpp_count and py_count > 0:
            detected_language = "Python"
            detected_framework = "FastAPI / Django / Flask"
        elif js_ts_count >= py_count and js_ts_count >= cpp_count and js_ts_count > 0:
            detected_language = "JavaScript / TypeScript"
            detected_framework = "Node.js / Express / Next.js"
        elif cpp_count > 0:
            detected_language = "C / C++"
            detected_framework = "C / C++ System Codebase"
        else:
            detected_language = "Universal Multi-Language"
            detected_framework = "Multi-Language Codebase"
    else:
        detected_language = "Java"
        detected_framework = "Spring Boot" if stereotype_counts.get("Controller", 0) > 0 else "Java Standard"
        if java_count >= (py_count + js_ts_count + cpp_count):
            repo_type = "Java Repository"
            analysis_scope = "Full Java Codebase"
        else:
            repo_type = "Hybrid Repository"
            analysis_scope = "Multi-Language Module"

    language_profile = {
        "java_files": java_count,
        "python_files": py_count,
        "js_ts_files": js_ts_count,
        "cpp_files": cpp_count,
        "build_system": build_system
    }

    repo_summary = {
        "repository": repo_root.name,
        "language": detected_language,
        "framework": detected_framework,
        "repo_type": repo_type,
        "analysis_scope": analysis_scope,
        "has_java_capability": has_java_capability,
        "build_system": build_system,
        "language_profile": language_profile,
        "controllers": stereotype_counts.get("Controller", 0),
        "services": stereotype_counts.get("Service", 0),
        "repositories": stereotype_counts.get("Repository", 0),
        "entities": stereotype_counts.get("Entity", 0),
        "rest_apis": total_endpoints,
        "total_classes": len(all_classes),
        "total_injected_dependencies": total_injected,
    }

    repo_model = {
        "repo": repo_root.name,
        "repo_summary": repo_summary,
        "stats": {
            "files_parsed": len(results),
            "files_failed": len(errors),
            "classes_found": len(all_classes),
            "methods_found": total_methods,
            "endpoints_found": total_endpoints,
            "stereotypes": stereotype_counts,
            "has_java_capability": has_java_capability,
            "repo_type": repo_type,
            "build_system": build_system
        },
        "classes": all_classes,
        "parse_errors": errors,
    }
    return repo_model
