"""
DevLensX Deep Reasoning Engine — explains WHAT the repo does, WHY it's architected this way,
and HOW components interact. Not just code paths — actual architectural reasoning.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import Counter, defaultdict

try:
    from devlensx.llm.provider import get_llm_provider
except Exception:
    get_llm_provider = None


# ---------------------------------------------------------------------------
# Schema adapters — the parser emits methods/constructors as separate nodes
# (stereotype Method/Constructor, kind method/constructor) linked to their
# class via metadata.parent_class synthetic ids (java_Name_<n>). Classes carry
# NO methods/fields lists, so all method/DI reasoning must go through this
# index. Shared with wiki_depth.extract_section_facts.
# ---------------------------------------------------------------------------

_NON_COMPONENT_STEREOTYPES = frozenset({"Method", "Endpoint", "Constructor", "Test", "DunderMethod"})
_NON_COMPONENT_KINDS = frozenset({"method", "constructor"})

# Human display names for parser language ids
LANG_DISPLAY = {
    "java": "Java", "python": "Python", "typescript": "TypeScript",
    "javascript": "JavaScript", "go": "Go", "rust": "Rust",
    "csharp": "C#", "cpp": "C++",
}

# Stereotypes that mark HTTP/API entry points across frameworks
ENTRY_STEREOTYPES = frozenset({"Controller", "Route", "Router", "Handler", "Endpoint", "View", "ViewSet"})
# Stereotypes that mark domain data across frameworks (ORM entities, pydantic models, TS types)
DATA_STEREOTYPES = frozenset({"Entity", "Model", "Schema", "Document", "Interface", "Type", "DTO"})


def handler_matches(handler: str, class_name: str) -> bool:
    """Token-boundary match: 'Owner' must NOT match 'OwnerController' handlers."""
    import re
    if not handler or not class_name:
        return False
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(class_name) + r"(?![A-Za-z0-9])", str(handler)) is not None


def simple_name(raw: str) -> str:
    """java_OwnerController_345 / py_AIPlayer_1 -> OwnerController / AIPlayer.

    Strips a lowercase language prefix (<lang>_) plus trailing _<digits>.
    """
    import re
    s = str(raw or "")
    m = re.match(r"^([a-z]{2,10})_(.+)_(\d+)$", s)
    if m and m.group(2)[:1].isupper():
        return m.group(2).split(".")[-1]
    if "_" in s:
        head, tail = s.rsplit("_", 1)
        if tail.isdigit() and head[:1].isupper():
            s = head
    return s.split(".")[-1]


def _has_parent(meta: Dict[str, Any]) -> bool:
    return bool((meta or {}).get("parent_class"))


def is_prod_component(c: Dict[str, Any]) -> bool:
    """True for real architectural units, not method/test nodes.

    Language-aware: TS/React top-level functions ARE components (no parent),
    but kind=function nodes WITH a parent_class link are methods.
    """
    if c.get("is_test"):
        return False
    if c.get("stereotype") in _NON_COMPONENT_STEREOTYPES:
        return False
    if c.get("kind") in _NON_COMPONENT_KINDS:
        return False
    if c.get("kind") == "function" and _has_parent(c.get("metadata") or {}):
        return False
    name = c.get("name", "")
    if name.startswith("__") and name.endswith("__"):
        return False
    if name.endswith("Test") or name.endswith("Tests"):
        return False
    return True


def build_method_index(classes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """parent simple class name -> method/ctor entries with signatures + params.

    Covers kind=method/constructor plus kind=function nodes that carry a
    parent_class link (Python/TS method style).
    """
    index: Dict[str, List[Dict[str, Any]]] = {}
    for c in classes:
        kind = c.get("kind")
        meta = c.get("metadata") or {}
        if kind not in ("method", "constructor") and not (kind == "function" and _has_parent(meta)):
            continue
        parent = simple_name(meta.get("parent_class") or "")
        if not parent:
            # Fall back to qualified_name head: pkg.Class.method -> Class
            qn = str(c.get("qualified_name", ""))
            parts = qn.split(".")
            parent = parts[-2] if len(parts) >= 2 else ""
        if not parent:
            continue
        index.setdefault(parent, []).append({
            "name": c.get("name", ""),
            "signature": c.get("signature") or "",
            "params": meta.get("parameters") or [],
            "annotations": c.get("annotations") or [],
            "is_ctor": kind == "constructor" or c.get("name") in ("__init__", "__construct__"),
            "is_test": bool(c.get("is_test")) or "Test" in (c.get("annotations") or []),
        })
    return index


def prod_methods(index: Dict[str, List[Dict[str, Any]]], class_name: str) -> List[Dict[str, Any]]:
    """Non-test methods for a class (ctors excluded)."""
    return [m for m in index.get(class_name, []) if not m["is_ctor"] and not m["is_test"]]


def ctor_params(index: Dict[str, List[Dict[str, Any]]], class_name: str) -> List[Dict[str, Any]]:
    """Constructor parameters (dependency injection evidence)."""
    out: List[Dict[str, Any]] = []
    for m in index.get(class_name, []):
        if m["is_ctor"]:
            out.extend(m["params"])
    return out


@dataclass
class ReasoningContext:
    """Structured context for reasoning about a codebase."""
    repo_name: str
    language: str
    framework: str
    total_classes: int
    stereotypes: Dict[str, int]
    key_components: List[Dict[str, Any]]
    request_flows: List[List[str]]
    tech_stack: List[Dict[str, str]]
    architectural_patterns: List[str]
    data_entities: List[str]
    external_integrations: List[str]
    security_concerns: List[str]
    performance_characteristics: List[str]
    module_relationships: Dict[str, List[str]]
    complexity_hotspots: List[Dict[str, Any]]


class DeepReasoningEngine:
    """Generates human-readable architectural explanations with evidence."""

    def __init__(self, model: Dict[str, Any], graph_store=None, verified_findings=None):
        self.model = model
        self.graph_store = graph_store
        self.verified_findings = verified_findings or []
        self.classes = model.get("classes", [])
        self.relationships = model.get("relationships", [])
        self.endpoints = model.get("endpoints", [])
        self.repo_summary = model.get("repo_summary", {})
        self._llm = None
        # Language family + framework evidence gates (avoid Spring claims on Python/TS)
        self.lang = str(self.repo_summary.get("language", "")).lower()
        self.lang_display = LANG_DISPLAY.get(self.lang, self.repo_summary.get("language", "Unknown"))
        anns = " ".join(str(c.get("annotations", [])) for c in self.classes)
        self.has_spring = "Controller" in anns or "Service" in anns or "Spring" in anns or "spring" in str(
            self.repo_summary.get("framework", ""))
        stereotypes = {c.get("stereotype") for c in self.classes}
        self.has_http_layer = bool(stereotypes & ENTRY_STEREOTYPES) or bool(self.endpoints)
        self.has_data_layer = bool(stereotypes & DATA_STEREOTYPES)

    def _controllers(self) -> List[Dict[str, Any]]:
        return [c for c in self.classes
                if is_prod_component(c) and c.get("stereotype") in ENTRY_STEREOTYPES]

    def _api_routes(self) -> List[str]:
        """Framework route handlers: Next.js route.ts GET/POST, Flask/FastAPI decorators etc."""
        routes = []
        for c in self.classes:
            if not is_prod_component(c):
                continue
            name, fpath = c.get("name", ""), str(c.get("file", "")).replace("\\", "/")
            # Next.js App Router: src/app/api/<path>/route.ts exporting GET/POST/...
            if (self.lang in ("typescript", "javascript") and name in ("GET", "POST", "PUT", "PATCH", "DELETE")
                    and "/api/" in fpath and "route." in fpath):
                try:
                    seg = fpath.split("/api/", 1)[1].rsplit("/route.", 1)[0]
                    routes.append(f"{name} /api/{seg}")
                except Exception:
                    routes.append(f"{name} {fpath}")
        return routes

    def _entities(self) -> List[Dict[str, Any]]:
        return [c for c in self.classes
                if is_prod_component(c) and (c.get("stereotype") in DATA_STEREOTYPES
                                             or str(c.get("name", "")).endswith("Entity"))]

    def _get_llm(self):
        if self._llm is not None or get_llm_provider is None:
            return self._llm
        try:
            self._llm = get_llm_provider("auto")
        except Exception:
            self._llm = False
        return self._llm

    def analyze(self) -> ReasoningContext:
        """Full architectural analysis with reasoning."""
        ctx = ReasoningContext(
            repo_name=self.model.get("repo", "repository"),
            language=self.repo_summary.get("language", "Unknown"),
            framework=self.repo_summary.get("framework", ""),
            total_classes=len([c for c in self.classes if is_prod_component(c)]),
            stereotypes=Counter(c.get("stereotype", "Unknown") for c in self.classes if not c.get("is_test")),
            key_components=[],
            request_flows=[],
            tech_stack=[],
            architectural_patterns=[],
            data_entities=[],
            external_integrations=[],
            security_concerns=[],
            performance_characteristics=[],
            module_relationships={},
            complexity_hotspots=[],
        )

        # Run all analyses
        ctx.key_components = self._identify_key_components()
        ctx.request_flows = self._trace_request_flows()
        ctx.tech_stack = self._analyze_tech_stack()
        ctx.architectural_patterns = self._detect_patterns()
        ctx.data_entities = self._identify_data_entities()
        ctx.external_integrations = self._detect_external_integrations()
        ctx.security_concerns = self._assess_security()
        ctx.performance_characteristics = self._assess_performance()
        ctx.module_relationships = self._map_module_relationships()
        ctx.complexity_hotspots = self._find_complexity_hotspots()

        return ctx

    def _identify_key_components(self) -> List[Dict[str, Any]]:
        """Find architecturally significant components with reasoning."""
        fan_in = Counter()
        fan_out = Counter()
        for r in self.relationships:
            src = simple_name(r.get("source", ""))
            tgt = simple_name(r.get("target", ""))
            if src: fan_out[src] += 1
            if tgt: fan_in[tgt] += 1

        method_index = build_method_index(self.classes)
        prod_classes = [c for c in self.classes if is_prod_component(c)]
        scored = []
        for c in prod_classes:
            name = c["name"]
            stereo = c.get("stereotype", "Component")
            methods = prod_methods(method_index, name)
            ctors = ctor_params(method_index, name)
            annotations = c.get("annotations", []) or []
            ep_count = sum(1 for e in self.endpoints if handler_matches(str(e.get("handler", "")), name))

            # Architectural significance score
            score = (
                fan_in.get(name, 0) * 3 +      # How many depend on this
                fan_out.get(name, 0) * 1 +     # How many this depends on
                len(methods) * 0.5 +           # Behavioral complexity
                len(annotations) * 1 +         # Framework integration
                ep_count * 2 +                 # HTTP surface area
                (2 if stereo in ("Controller", "Service", "Repository") else 0)
            )
            # Pure type declarations are wiring, not behavior — demote
            if stereo in ("Interface", "Type", "DTO"):
                score *= 0.3

            # Reasoning for why this matters (language-agnostic first)
            reasons = []
            if fan_in.get(name, 0) > 3:
                reasons.append(f"High fan-in ({fan_in[name]} components depend on it) — central abstraction")
            if ep_count:
                reasons.append(f"Entry point for {ep_count} HTTP endpoint(s)")
            if len(methods) >= 5 and stereo not in ("Service", "Repository"):
                unit = "operations" if self.lang != "typescript" else "render paths/handlers"
                reasons.append(f"Behavioral hub ({len(methods)} {unit})")
            if stereo == "Service":
                reasons.append(f"Business logic orchestrator ({len(methods)} operations)")
            if stereo == "Repository":
                reasons.append(f"Data access layer ({len(methods)} query methods)")
            if ctors:
                deps = ", ".join((p.get("type", "") or p.get("name", "?")).strip() or "?" for p in ctors[:3])
                if self.has_spring and stereo in ("Service", "Controller"):
                    reasons.append(f"Constructor injection ({deps}) — testable, decoupled design")
                elif deps and deps != "?":
                    reasons.append(f"Constructed with ({deps}) — explicit dependencies")
            if any("Transactional" in str(a) for a in annotations):
                reasons.append("Manages transaction boundaries")

            scored.append({
                "name": name,
                "stereotype": stereo,
                "score": score,
                "methods": len(methods),
                "fan_in": fan_in.get(name, 0),
                "fan_out": fan_out.get(name, 0),
                "reasoning": reasons,
                "key_methods": [(m["signature"] or m["name"]) for m in methods[:5]],
                "annotations": annotations[:3],
            })

        scored.sort(key=lambda x: (-x["score"], x["name"]))
        # Behavioral units first; pure type declarations trail (still ranked for blast radius)
        behavioral = [s for s in scored if s["stereotype"] not in ("Interface", "Type", "DTO")]
        types = [s for s in scored if s["stereotype"] in ("Interface", "Type", "DTO")]
        return (behavioral + types)[:10]

    def _trace_request_flows(self) -> List[List[str]]:
        """Trace realistic request paths through the architecture."""
        flows = []
        controllers = [c for c in self.classes if c.get("stereotype") == "Controller" and not c.get("is_test")]

        for ctrl in controllers[:3]:  # Top 3 controllers
            path = [ctrl["name"]]
            # Follow dependencies
            current = ctrl["name"]
            for _ in range(3):  # Max 3 hops
                downstreams = []
                for r in self.relationships:
                    src = simple_name(r.get("source", ""))
                    tgt = simple_name(r.get("target", ""))
                    if (src == current or current in str(r.get("source", ""))) and tgt and tgt not in path:
                        downstreams.append(tgt)
                if downstreams:
                    # Prefer Service -> Repository
                    services = [d for d in downstreams if any(c["name"]==d and c.get("stereotype")=="Service" for c in self.classes)]
                    repos = [d for d in downstreams if any(c["name"]==d and c.get("stereotype")=="Repository" for c in self.classes)]
                    next_node = (services + repos + downstreams)[0]
                    path.append(next_node)
                    current = next_node
                else:
                    break
            if len(path) > 1:
                flows.append(path)
        return flows

    def _analyze_tech_stack(self) -> List[Dict[str, str]]:
        """Detect and explain technology choices (per-language, evidence-gated)."""
        stack = []

        if self.lang_display and self.lang_display != "Unknown":
            n_prod = len([c for c in self.classes if is_prod_component(c)])
            stack.append({"tech": self.lang_display, "role": "Primary language",
                          "reason": f"{n_prod} production components parsed"})

        fw = self.repo_summary.get("framework", "")
        if fw:
            stack.append({"tech": fw, "role": "Framework",
                          "reason": "Detected from manifests, annotations, and dependency declarations"})
        for f in (self.model.get("frameworks", []) or [])[:3]:
            name = f.get("name") if isinstance(f, dict) else str(f)
            if name and name != fw:
                stack.append({"tech": name, "role": "Framework",
                              "reason": "Detected from project manifests"})

        # Detect specific patterns
        annotations_flat = []
        for c in self.classes:
            annotations_flat.extend(c.get("annotations", []) or [])

        # Java/Spring only — never claim on Python/TS
        if self.has_spring:
            if any("Spring" in a or "spring" in a.lower() for a in annotations_flat):
                stack.append({"tech": "Spring Boot", "role": "DI Container + Web",
                              "reason": "@Controller, @Service, @Repository annotations pervasive"})
            if any("Lombok" in a or "lombok" in a.lower() for a in annotations_flat):
                stack.append({"tech": "Lombok", "role": "Boilerplate reduction",
                              "reason": "@RequiredArgsConstructor, @Data eliminate getter/setter/constructor noise"})
            if any("Transactional" in a for a in annotations_flat):
                stack.append({"tech": "Spring Transactions", "role": "Transaction management",
                              "reason": "@Transactional on service methods — declarative boundary control"})
            has_entities = any(c.get("stereotype") == "Entity" for c in self.classes)
            has_repos = any(c.get("stereotype") == "Repository" for c in self.classes)
            if has_entities and has_repos:
                stack.append({"tech": "JPA/Hibernate", "role": "ORM",
                              "reason": "@Entity domain classes + Repository interfaces with finder methods"})

        # Python idioms
        if self.lang == "python":
            if any(c.get("stereotype") == "Model" for c in self.classes):
                stack.append({"tech": "Pydantic-style models", "role": "Data validation",
                              "reason": "Model-stereotype classes define validated schemas"})
            if any("pytest" in str(c.get("file", "")).lower() or c.get("stereotype") == "Test" for c in self.classes):
                stack.append({"tech": "pytest", "role": "Test runner",
                              "reason": "Test files/cases present in the repository"})

        # TypeScript idioms
        if self.lang in ("typescript", "javascript"):
            if any(c.get("stereotype") == "Hook" for c in self.classes):
                stack.append({"tech": "React Hooks", "role": "Stateful logic",
                              "reason": "Hook-stereotype functions colocate state with components"})

        # Build tool (repo_summary first, model files second)
        build_system = self.repo_summary.get("build_system", "")
        if build_system and build_system not in ("Unknown", ""):
            stack.append({"tech": build_system, "role": "Build system",
                          "reason": "Detected from project manifests"})
        else:
            build_files = self.model.get("build_files", []) or []
            if any("gradle" in f.lower() for f in build_files):
                stack.append({"tech": "Gradle", "role": "Build system", "reason": "build.gradle(.kts) present"})
            elif any("maven" in f.lower() or "pom.xml" in f.lower() for f in build_files):
                stack.append({"tech": "Maven", "role": "Build system", "reason": "pom.xml present"})

        # Dedupe by tech name, keep the most informative entry
        seen: Dict[str, Dict[str, str]] = {}
        for item in stack:
            key = item["tech"].lower()
            if key not in seen or len(item["reason"]) > len(seen[key]["reason"]):
                seen[key] = item
        return list(seen.values())

    def _detect_patterns(self) -> List[str]:
        """Identify architectural patterns in use (per-language idioms)."""
        patterns = []
        stereotypes = {c.get("stereotype") for c in self.classes}
        names = [c.get("name", "") for c in self.classes]

        if "Controller" in stereotypes and "Service" in stereotypes and "Repository" in stereotypes:
            patterns.append("Layered Architecture (Controller → Service → Repository) — clear separation of concerns")
        elif self.has_http_layer and self.has_data_layer:
            patterns.append("Layered request handling — HTTP entry points delegate to a data layer")

        if "Entity" in stereotypes and self.has_spring:
            patterns.append("Domain-Driven Design — explicit Entity/Model layer with JPA mapping")
        elif "Model" in stereotypes and self.lang == "python":
            patterns.append("Pydantic-style Models — validated data schemas separate from logic")
        elif "Interface" in stereotypes and self.lang in ("typescript", "javascript"):
            patterns.append("Type-first Design — explicit interfaces separate contracts from components")

        # React / UI idioms
        if "Hook" in stereotypes:
            hooks = [c["name"] for c in self.classes if c.get("stereotype") == "Hook"][:3]
            patterns.append(f"React Hooks state ({', '.join(hooks)}) — colocated stateful logic")
        if any("Provider" in n or "Context" in n for n in names):
            patterns.append("Provider/Context pattern — dependency injection via React context")

        # Python idioms
        if self.lang == "python" and any(n == "main" or "cli" in n.lower() for n in names):
            patterns.append("Script/CLI entry point — runnable module with a main routine")

        # Check for constructor injection: params must reference KNOWN components,
        # otherwise it's just data (e.g. Game(board_size)) — not DI.
        method_index = build_method_index(self.classes)
        known = {c["name"] for c in self.classes if is_prod_component(c)}
        injected = []
        for c in self.classes:
            if not is_prod_component(c):
                continue
            for p in ctor_params(method_index, c["name"]):
                ptype = (p.get("type", "") or "").strip()
                if ptype in known and ptype != c["name"]:
                    injected.append(c["name"])
                    break
        if injected:
            if self.has_spring:
                patterns.append(
                    "Constructor-based Dependency Injection "
                    f"({', '.join(injected[:4])}) — enables immutability and testability"
                )
            else:
                patterns.append(
                    "Explicit constructor wiring "
                    f"({', '.join(injected[:4])}) — collaborators passed in, not constructed inline"
                )

        # Check for interface-based repositories
        repos = [c for c in self.classes if c.get("stereotype") == "Repository"]
        if repos and any(c.get("kind") == "interface" for c in repos):
            patterns.append("Repository Pattern with Interfaces — implementation hidden behind abstraction")

        # Check for DTO pattern
        dtos = [c for c in self.classes if "DTO" in c.get("name", "").upper() or "Request" in c.get("name", "") or "Response" in c.get("name", "")]
        if dtos:
            patterns.append("DTO Pattern — separate API contracts from domain model")

        # Check for Mapper pattern
        mappers = [c for c in self.classes if "Mapper" in c.get("name", "")]
        if mappers:
            patterns.append("Mapper Pattern — explicit entity↔DTO conversion")

        # Check for exception handling
        if any("ExceptionHandler" in str(c.get("annotations", [])) or "ControllerAdvice" in str(c.get("annotations", [])) for c in self.classes):
            patterns.append("Centralized Exception Handling — @ControllerAdvice for consistent error responses")

        return patterns or ["No strong architectural patterns detected — flat structure"]

    def _identify_data_entities(self) -> List[str]:
        """Find core domain entities, ranked by fan-in (concrete domain first)."""
        fan_in = Counter()
        for r in self.relationships:
            fan_in[simple_name(r.get("target", ""))] += 1
        scored = []
        for c in self.classes:
            if not is_prod_component(c):
                continue
            stereo = c.get("stereotype", "")
            name = c.get("name", "")
            if stereo in ("Entity", "Model") or name.endswith("Entity"):
                anns = ", ".join(f"@{a}" for a in (c.get("annotations", []) or [])[:3])
                span = (c.get("line_end") or 0) - (c.get("line_start") or 0)
                detail = anns if anns else f"{span} lines"
                # Prefer concrete entities over abstract base classes
                base_penalty = -5 if "MappedSuperclass" in anns or "Base" in name else 0
                scored.append((fan_in.get(name, 0) + base_penalty, name, f"{name} ({detail})"))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [s[2] for s in scored[:8]]

    def _detect_external_integrations(self) -> List[str]:
        """Detect external systems the codebase integrates with."""
        integrations = set()
        keywords = {
            "redis": "Redis (caching/sessions)",
            "kafka": "Apache Kafka (event streaming)",
            "rabbitmq": "RabbitMQ (message broker)",
            "elasticsearch": "Elasticsearch (search)",
            "mongodb": "MongoDB (document store)",
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "dynamodb": "DynamoDB",
            "s3": "AWS S3",
            "azure": "Azure Services",
            "grpc": "gRPC",
            "graphql": "GraphQL",
        }

        all_text = " ".join([
            c.get("name", "") + " " + str(c.get("annotations", [])) + " " + str(c.get("fields", []))
            for c in self.classes
        ]).lower()

        for kw, desc in keywords.items():
            if kw in all_text:
                integrations.add(desc)

        return list(integrations)

    def _assess_security(self) -> List[str]:
        """Security-relevant architectural observations."""
        concerns = []
        findings = self.verified_findings

        for f in findings:
            cat = str(f.get("category", "")).lower()
            if "secur" in cat or "auth" in cat or "injection" in cat:
                concerns.append(f"{f.get('title', 'Security finding')}: {f.get('reason', f.get('claim', ''))[:150]}")

        # Architectural security patterns
        has_security_config = any("SecurityConfig" in c.get("name", "") or "WebSecurity" in c.get("name", "") for c in self.classes)
        if has_security_config:
            concerns.append("Security configuration present — centralized authN/authZ setup detected")

        has_cors = any("Cors" in c.get("name", "") or "cors" in str(c.get("annotations", [])).lower() for c in self.classes)
        if has_cors:
            concerns.append("CORS configuration detected — cross-origin policies defined")

        return concerns[:6]

    def _assess_performance(self) -> List[str]:
        """Performance characteristics from architecture (evidence-gated)."""
        perf = []

        # N+1 risk — only when a service→repository layering actually exists
        services = [c for c in self.classes if c.get("stereotype") == "Service"]
        repos = [c for c in self.classes if c.get("stereotype") == "Repository"]
        if services and repos and self.has_spring:
            perf.append("Potential N+1 query risk — Service→Repository pattern without explicit fetch strategies")

        # Caching — only when cache evidence exists (not mere name coincidence)
        has_cache_anno = any("Cacheable" in str(c.get("annotations", [])) or "CacheEvict" in str(c.get("annotations", []))
                             for c in self.classes)
        has_cache_config = any("CacheConfig" in c.get("name", "") or "CacheManager" in c.get("name", "") for c in self.classes)
        if has_cache_anno:
            perf.append("Caching annotations detected — @Cacheable on repository/service methods")
        elif has_cache_config:
            perf.append("Cache configuration present — explicit cache region setup detected")

        method_index = build_method_index(self.classes)
        all_sigs = " ".join(
            (m.get("signature") or m.get("name", ""))
            for ms in method_index.values() for m in ms
        )
        # Async
        has_async = any("@Async" in str(c.get("annotations", [])) for c in self.classes) or "CompletableFuture" in all_sigs
        if has_async and self.has_spring:
            perf.append("Async processing — @Async or CompletableFuture for non-blocking operations")
        elif "async " in all_sigs and self.lang == "python":
            perf.append("Async functions present — asyncio-style non-blocking operations")
        elif "async" in all_sigs and self.lang in ("typescript", "javascript"):
            perf.append("Async functions present — promise-based non-blocking operations")

        # Pagination
        if "Page<" in all_sigs or "Slice<" in all_sigs or "Pageable" in all_sigs:
            if self.has_spring:
                perf.append("Pagination support — Spring Data Page/Slice return types on repositories")
            else:
                perf.append("Pagination support — paged query signatures detected")

        return perf[:5]

    def _map_module_relationships(self) -> Dict[str, List[str]]:
        """Map package/module level relationships (via class package lookup)."""
        pkg_of = {c["name"]: (c.get("package") or "root") for c in self.classes if is_prod_component(c)}
        pkg_edges: Dict[str, Set[str]] = defaultdict(set)
        for r in self.relationships:
            src_pkg = pkg_of.get(simple_name(r.get("source", "")), "")
            tgt_pkg = pkg_of.get(simple_name(r.get("target", "")), "")
            if src_pkg and tgt_pkg and src_pkg != tgt_pkg:
                pkg_edges[src_pkg].add(tgt_pkg)

        return {k: sorted(v) for k, v in pkg_edges.items()}

    def _find_complexity_hotspots(self) -> List[Dict[str, Any]]:
        """Identify classes with high complexity."""
        method_index = build_method_index(self.classes)
        hotspots = []
        for c in self.classes:
            if not is_prod_component(c):
                continue
            n_methods = len(prod_methods(method_index, c["name"]))
            span = (c.get("line_end") or 0) - (c.get("line_start") or 0)
            complexity = n_methods + span / 50.0
            if complexity > 12:
                hotspots.append({
                    "name": c["name"],
                    "stereotype": c.get("stereotype", "Component"),
                    "methods": n_methods,
                    "lines": span,
                    "complexity_score": round(complexity, 1),
                    "concern": f"{n_methods} methods / {span} lines — consider decomposition"
                })
        hotspots.sort(key=lambda x: -x["complexity_score"])
        return hotspots[:5]

    def generate_narrative(self, ctx: ReasoningContext) -> Dict[str, str]:
        """Generate human-readable narrative explanations for each wiki section."""
        llm = self._get_llm()
        use_llm = llm and llm is not False

        narratives = {}

        # 1. What this project DOES (not code structure)
        narratives["purpose"] = self._generate_purpose(ctx, use_llm)

        # 2. Architecture philosophy
        narratives["architecture"] = self._generate_architecture(ctx, use_llm)

        # 3. Key components with reasoning
        narratives["components"] = self._generate_components(ctx, use_llm)

        # 4. Request flow explanation
        narratives["flow"] = self._generate_flow(ctx, use_llm)

        # 5. Technology rationale
        narratives["tech"] = self._generate_tech_rationale(ctx, use_llm)

        # 6. Risks and trade-offs
        narratives["risks"] = self._generate_risks(ctx, use_llm)

        # 7. Where to look next
        narratives["risks_enriched"] = self._generate_risks_enriched(ctx, use_llm)
        narratives["getting_started"] = self._generate_getting_started(ctx)
        narratives["data_model"] = self._generate_data_model(ctx)
        narratives["next"] = self._generate_next_steps(ctx)

        return narratives

    def _generate_purpose(self, ctx: ReasoningContext, use_llm: bool) -> str:
        llm = self._get_llm()
        if use_llm and llm:
            try:
                routes = [f"{e.get('method','GET')} {e.get('path','')}".strip() for e in self.endpoints] + self._api_routes()
                comps = [f"{c['name']} ({c['stereotype']})" for c in ctx.key_components[:6]]
                prompt = f"""You are a principal software architect writing production-grade technical onboarding documentation for a repository named `{ctx.repo_name}`.

Repository Metadata:
- Primary Language: {ctx.language}
- Framework / Runtime: {ctx.framework or 'Modular'}
- Total Prod Components: {ctx.total_classes}
- Core Domain Entities: {', '.join(ctx.data_entities[:6]) or 'None detected'}
- Key Architectural Units: {', '.join(comps) or 'General modules'}
- Exposed HTTP Endpoints / Routes ({len(routes)} detected): {', '.join(routes[:6]) or 'Internal package / library (no direct HTTP routes)'}
- Architectural Patterns: {', '.join(ctx.architectural_patterns) or 'Modular architecture'}

Write a comprehensive, in-depth architectural introduction and purpose summary (2-3 structured paragraphs):
1. What this repository builds or accomplishes from an application and domain standpoint.
2. The primary architectural role of the key components ({', '.join([c['name'] for c in ctx.key_components[:4]])}).
3. How external consumers or user requests interface with the codebase.

Be concrete, authoritative, and fact-grounded. Reference actual component names and endpoints. No generic filler."""
                res = llm.generate(prompt=prompt, system_prompt="You are DevLensX DeepWiki AI — synthesizing grounded repository intelligence.")
                if res and len(res.strip()) > 60:
                    return res.strip()
            except Exception:
                pass

        # Deterministic fallback — branch by what the repo actually contains
        lang = self.lang_display
        parts = []
        entry_pts = [c for c in ctx.key_components if c["stereotype"] in ENTRY_STEREOTYPES]
        if self.endpoints and entry_pts:
            parts.append(
                f"This {lang} system exposes **{len(self.endpoints)} HTTP endpoints** through "
                f"**{', '.join(c['name'] for c in entry_pts[:3])}**."
            )
        api_routes = self._api_routes()
        if api_routes and not self.endpoints:
            shown = ", ".join(f"`{r}`" for r in api_routes[:3])
            opener = f"This {lang} system serves" if not parts else "It serves"
            parts.append(f"{opener} API routes ({shown}).")
        # UI-component tree (React etc.) — composes with API/data sentences, not instead
        ui_comps = [c for c in ctx.key_components if c["stereotype"] == "Component"]
        ui_hooks = [c["name"] for c in ctx.key_components if c["stereotype"] == "Hook"]
        if ui_comps and self.lang in ("typescript", "javascript"):
            hook_txt = f", state via **{', '.join(ui_hooks[:2])}**" if ui_hooks else ""
            parts.append(
                f"The UI is composed of **{len(ui_comps)} components** "
                f"(**{', '.join(c['name'] for c in ui_comps[:4])}**{hook_txt})."
            )
        if ctx.data_entities and not ui_comps:
            noun = "domain entities" if self.has_http_layer or self.lang == "java" else "core data types"
            parts.append(f"It manages **{', '.join(ctx.data_entities[:3])}** as its {noun}.")
        if not parts:
            # Class/function-centric codebase (Python scripts, games, libs)
            behaved = [c for c in ctx.key_components
                       if c["stereotype"] in ("Class", "Function", "Service", "Component")][:4]
            top = [c["name"] for c in behaved] or [c["name"] for c in ctx.key_components[:3]]
            if top:
                what = "implements its logic" if self.lang == "python" else "centers its implementation"
                parts.append(f"This {lang} codebase {what} in **{', '.join(top)}**.")
        if not parts:
            parts.append(f"This {lang} repository was analyzed; see components below.")
        # Prefer the most specific architectural pattern for the closing line
        arch_line = ""
        if ctx.architectural_patterns:
            specific = next((p for p in ctx.architectural_patterns
                             if "Layered request handling" not in p), ctx.architectural_patterns[0])
            arch_line = f"Architecture: **{specific}**."
        if arch_line:
            parts.append(arch_line)
        return " ".join(parts) or "Repository structure analyzed; see components below."

    def _generate_architecture(self, ctx: ReasoningContext, use_llm: bool) -> str:
        llm = self._get_llm()
        if use_llm and llm:
            try:
                prompt = f"""You are a principal software architect explaining the architecture philosophy for `{ctx.repo_name}`.

Context:
- Primary Language: {ctx.language}
- Framework: {ctx.framework or 'Standard'}
- Inferred Architectural Patterns: {', '.join(ctx.architectural_patterns) or 'Modular Structure'}
- Component Stereotypes: {dict(ctx.stereotypes)}
- Key Modules & Relationships: {dict(list(ctx.module_relationships.items())[:5])}
- External Integrations: {', '.join(ctx.external_integrations) or 'Self-contained / internal standard library'}

Explain the architectural philosophy in 2-3 structured paragraphs:
1. Explain WHY the repository is partitioned into these specific layers or modules.
2. How dependencies and data flow across component boundaries.
3. Key trade-offs made in this architecture (e.g. coupling vs modularity, simplicity vs extensibility)."""
                res = llm.generate(prompt=prompt, system_prompt="You are a principal software architect explaining system design.")
                if res and len(res.strip()) > 60:
                    return res.strip()
            except Exception:
                pass

        parts = []
        if ctx.architectural_patterns:
            parts.append(f"**Architectural Style:** {ctx.architectural_patterns[0]}")
            for p in ctx.architectural_patterns[1:3]:
                parts.append(f"• {p}")

        layer_order = ["Controller", "Route", "Handler", "Service", "Repository", "Model", "Entity",
                       "Component", "Hook", "Function", "Class"]
        layers = [s for s in layer_order if s in ctx.stereotypes]
        if layers:
            parts.append(f"**Layer Stack:** {' → '.join(layers)} — each layer has a single responsibility.")
        return "\n\n".join(parts)

    def _generate_components(self, ctx: ReasoningContext, use_llm: bool) -> str:
        if not ctx.key_components:
            return "No significant components identified."

        llm = self._get_llm()
        if use_llm and llm:
            try:
                comp_descriptions = []
                for c in ctx.key_components[:6]:
                    methods = c.get("key_methods", [])
                    reasons = c.get("reasoning", [])
                    comp_descriptions.append(f"- {c['name']} ({c['stereotype']}): {'; '.join(reasons[:2])}. Ops: {', '.join(methods[:3])}")
                prompt = f"""Format and explain the top architectural components for repository `{ctx.repo_name}`:
{chr(10).join(comp_descriptions)}

Provide a concise breakdown for each component explaining its role in the system, its collaboration with other components, and why it is critical."""
                res = llm.generate(prompt=prompt, system_prompt="Software architect detailing component responsibilities.")
                if res and len(res.strip()) > 60:
                    return res.strip()
            except Exception:
                pass

        lines = []
        for c in ctx.key_components[:6]:
            reasons = c.get("reasoning", [])
            reason_text = "; ".join(reasons[:2]) if reasons else "Core component"
            methods = c.get("key_methods", [])
            method_text = f" — key ops: {', '.join(methods[:3])}" if methods else ""
            lines.append(f"**{c['name']}** ({c['stereotype']}): {reason_text}{method_text}")

        return "\n\n".join(lines)

    def _generate_flow(self, ctx: ReasoningContext, use_llm: bool) -> str:
        if not ctx.request_flows:
            return "No clear request flows traced."

        llm = self._get_llm()
        if use_llm and llm:
            try:
                flow_traces = [f"Flow {i}: {' -> '.join(f)}" for i, f in enumerate(ctx.request_flows[:3], 1)]
                prompt = f"""Explain the lifecycle of an incoming operation or request in `{ctx.repo_name}` based on these detected component traces:
{chr(10).join(flow_traces)}

Explain step-by-step how data enters the system, which components handle validation and business logic, how persistence or downstream services are engaged, and how responses return to the caller."""
                res = llm.generate(prompt=prompt, system_prompt="Software architect explaining execution flows.")
                if res and len(res.strip()) > 60:
                    return res.strip()
            except Exception:
                pass

        lines = []
        for i, flow in enumerate(ctx.request_flows[:3], 1):
            lines.append(f"**Flow {i}:** {' → '.join(flow)}")
            if len(flow) >= 3:
                lines.append(f"Controller **{flow[0]}** receives request, delegates to **{flow[1]}** for business logic, which uses **{flow[2]}** for data access.")
        return "\n\n".join(lines)

    def _generate_tech_rationale(self, ctx: ReasoningContext, use_llm: bool) -> str:
        if not ctx.tech_stack:
            return "Stack inferred from parser output."

        lines = []
        for item in ctx.tech_stack:
            lines.append(f"**{item['tech']}** ({item['role']}): {item['reason']}")
        return "\n\n".join(lines)

    def _generate_risks(self, ctx: ReasoningContext, use_llm: bool) -> str:
        items = []
        if ctx.security_concerns:
            items.append("**Security:**\n" + "\n".join(f"• {c}" for c in ctx.security_concerns[:3]))
        if ctx.performance_characteristics:
            items.append("**Performance:**\n" + "\n".join(f"• {p}" for p in ctx.performance_characteristics[:3]))
        if ctx.complexity_hotspots:
            items.append("**Complexity Hotspots:**\n" + "\n".join(f"• {h['name']} ({h['stereotype']}) — {h['concern']}" for h in ctx.complexity_hotspots[:3]))
        return "\n\n".join(items) if items else "No significant risks detected in architecture."

    def _generate_risks_enriched(self, ctx: ReasoningContext, use_llm: bool) -> str:
        """Risks with issue-type primitives (BUG_RISK/SECURITY/etc.) inferred
        per hotspot from its kind and placement — the missing link between
        hotspot text and the Evaluation Lab / Change Impact views."""
        # Keep this deterministic: categorize then derive RISK from provenance.
        issue_map = {
            "Controller": ("BUG_RISK", "HIGH — HTTP entry point; sender-role compromise path."),
            "Service": ("SECURITY", "MEDIUM — orchestrates repository calls; boundary-sensitive."),
            "Repository": ("PERFORMANCE", "MEDIUM — query-heavy path; N+1/batch risk."),
        }
        parts = [self._generate_risks(ctx, use_llm)]
        hotspots = ctx.complexity_hotspots[:3]
        if hotspots:
            enriched = []
            for h in hotspots:
                stereo = str(h.get("stereotype", ""))
                base = issue_map.get(stereo)
                if base:
                    issue, risk = base
                    enriched.append(f"• **{issue}** · `{h['name']}` ({stereo}) — {risk}")
            if enriched:
                parts.append("**By Issue Type:**\n" + "\n".join(enriched))
        return "\n\n".join(p for p in parts if p)

    def _generate_getting_started(self, ctx: ReasoningContext) -> str:
        """RepoMind-style quickstart strictly derived from actual manifests — never invented."""
        from devlensx.reasoning.engine import RepositoryReasoningEngine
        reasoner = RepositoryReasoningEngine()
        info = reasoner.extract_manifest_instructions(self.model)

        if not info.get("has_manifest"):
            return (
                "**INSUFFICIENT_EVIDENCE / NOT_FOUND**\n\n"
                "No supported build manifests (such as `pom.xml`, `package.json`, `pyproject.toml`, or `Cargo.toml`) "
                "were detected in this repository. DevLensX does not invent build or run commands without verifiable manifest evidence."
            )

        lines = []
        prereqs = info.get("prerequisites", [])
        if prereqs:
            lines.append(f"**Prerequisites:** {', '.join(prereqs)}")
        if info.get("install"):
            lines.append(f"**Install:** `{info['install']}`")
        if info.get("build"):
            lines.append(f"**Build:** `{info['build']}`")
        if info.get("run"):
            lines.append(f"**Run:** `{info['run']}`")
        if info.get("test"):
            lines.append(f"**Test:** `{info['test']}`")
        if info.get("notes"):
            lines.append(f"**Notes:** {info['notes']}")

        return "\n".join(f"- {l}" for l in lines)

    def _generate_data_model(self, ctx: ReasoningContext) -> str:
        """RepoMind data model: entities, relationships, and persistence."""
        if not ctx.data_entities:
            return "No explicit domain entities detected — this codebase is logic/UI-centric, not data-centric."
        lines = [f"This repository's data layer centers on **{len(ctx.data_entities)} entities**:"]
        for ent in ctx.data_entities[:6]:
            lines.append(f"- {ent}")
        # Try to infer relationships from edges
        if self.relationships:
            rels = [r for r in self.relationships if any(e in str(r.get("source","")) for e in [c.split()[0] for c in ctx.data_entities[:3]])]
            if rels:
                lines.append("\n**Key relationships:**")
                for r in rels[:4]:
                    lines.append(f"- `{r.get('source','')} → {r.get('target','')}` ({r.get('type','')})")
        if any("JPA" in t or "ORM" in t for t in [d.get("tech","") for d in ctx.tech_stack]):
            lines.append("\nPersistence via JPA/Hibernate — entities map to relational tables, repositories are Spring Data interfaces.")
        return "\n".join(lines)

    def _generate_next_steps(self, ctx: ReasoningContext) -> str:
        # Enhanced with getting-started awareness
        steps = [
            f"Start with **{ctx.key_components[0]['name']}** ({ctx.key_components[0]['stereotype']}) — highest architectural impact" if ctx.key_components else "Explore the Architecture page for system overview",
            f"Trace request flow: **{' → '.join(ctx.request_flows[0])}**" if ctx.request_flows else "Check API Reference for endpoint mappings",
            f"Review **{ctx.data_entities[0]}** entity and its repository" if ctx.data_entities else "Examine Module pages for package-level detail",
        ]
        # Add quickstart-driven step
        if ctx.tech_stack:
            steps.append(f"Then run it locally — see **Getting Started** above for `{ctx.tech_stack[0]['tech']}` setup.")
        return "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))


# Convenience function for wiki integration
def build_deep_reasoning(model: Dict[str, Any], graph_store=None, verified_findings=None) -> Tuple[ReasoningContext, Dict[str, str]]:
    """One-call entry point: returns context + narratives."""
    engine = DeepReasoningEngine(model, graph_store, verified_findings)
    ctx = engine.analyze()
    narratives = engine.generate_narrative(ctx)
    return ctx, narratives