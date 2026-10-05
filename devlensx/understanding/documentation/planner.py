"""
DevLensX Dynamic Documentation Planner
Generates adaptive Wiki navigation trees and Bounded Evidence Packages from RepositoryBrain evidence.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from devlensx.understanding.model.repository_brain import RepositoryBrain
from devlensx.understanding.documentation.models import (
    DocumentationTree,
    DocumentationPage,
    DocumentationSection,
    PageEvidenceScope,
    RepositoryProfile,
    PageType,
    CapabilityFlag,
    DocumentationCacheKey,
)


class DocumentationPlanner:
    """Generates adaptive documentation tree from RepositoryBrain evidence."""

    MANDATORY_PAGES = [
        PageType.OVERVIEW,
        PageType.GETTING_STARTED,
        PageType.PROJECT_STRUCTURE,
        PageType.CORE_ARCHITECTURE,
        PageType.GLOSSARY,
    ]

    CONDITIONAL_PAGES = [
        PageType.COMPONENTS,
        PageType.FEATURES,
        PageType.DATA_LAYER,
        PageType.API_ROUTES,
        PageType.STATE_MANAGEMENT,
        PageType.DEPENDENCIES,
        PageType.CONFIGURATION,
        PageType.TESTING,
        PageType.SECURITY,
        PageType.INFRASTRUCTURE,
        PageType.DEPLOYMENT,
        PageType.GIT_HISTORY,
        PageType.RUNTIME_FLOW,
        PageType.DOMAIN_ARCHITECTURE,
    ]

    PAGE_TYPE_METADATA = {
        PageType.OVERVIEW: {"title": "Overview", "icon": "book", "order": 0, "is_mandatory": True},
        PageType.GETTING_STARTED: {"title": "Getting Started", "icon": "rocket", "order": 1, "is_mandatory": True},
        PageType.PROJECT_STRUCTURE: {"title": "Project Structure", "icon": "folder", "order": 2, "is_mandatory": True},
        PageType.CORE_ARCHITECTURE: {"title": "Core Architecture", "icon": "cpu", "order": 3, "is_mandatory": True},
        PageType.COMPONENTS: {"title": "Components", "icon": "layout", "order": 10},
        PageType.FEATURES: {"title": "Features", "icon": "sparkles", "order": 11},
        PageType.DATA_LAYER: {"title": "Data Layer", "icon": "database", "order": 12},
        PageType.API_ROUTES: {"title": "API / Routes", "icon": "globe", "order": 13},
        PageType.STATE_MANAGEMENT: {"title": "State Management", "icon": "database", "order": 14},
        PageType.DEPENDENCIES: {"title": "Dependencies", "icon": "package", "order": 15},
        PageType.CONFIGURATION: {"title": "Configuration", "icon": "settings", "order": 16},
        PageType.TESTING: {"title": "Testing", "icon": "check-circle", "order": 17},
        PageType.SECURITY: {"title": "Security", "icon": "shield", "order": 18},
        PageType.INFRASTRUCTURE: {"title": "Infrastructure", "icon": "server", "order": 19},
        PageType.DEPLOYMENT: {"title": "Deployment", "icon": "cloud", "order": 20},
        PageType.GIT_HISTORY: {"title": "Git History", "icon": "git-branch", "order": 21},
        PageType.RUNTIME_FLOW: {"title": "Runtime Flow", "icon": "git-merge", "order": 22},
        PageType.DOMAIN_ARCHITECTURE: {"title": "Domain Architecture", "icon": "git-fork", "order": 23},
        PageType.GLOSSARY: {"title": "Glossary", "icon": "list", "order": 99, "is_mandatory": True},
    }

    def __init__(self, brain: RepositoryBrain):
        self.brain = brain
        self.repo_path = brain.repo_path
        self.analysis_run_id = brain.analysis_run_id

        # Normalize class file paths to be relative to the repo root so that
        # directory clustering never treats the repository's own folder as a
        # domain segment (prevents e.g. a "Sp Portfolio" cluster).
        self.classes: List[Dict[str, Any]] = []
        for c in brain.classes:
            c = dict(c)
            raw_file = (c.get("file") or "").replace("\\", "/")
            try:
                rel = str(Path(raw_file).relative_to(Path(self.repo_path).resolve())).replace("\\", "/")
            except Exception:
                # Strip the repo folder name prefix heuristically
                repo_folder = Path(self.repo_path).name
                parts = raw_file.split("/")
                if repo_folder in parts:
                    parts = parts[parts.index(repo_folder) + 1:]
                    rel = "/".join(parts)
                else:
                    rel = raw_file
            c["file"] = rel
            self.classes.append(c)

        self.profile = brain.profile
        self.capabilities = brain.capabilities
        self.flows = brain.flows
        self.architecture = brain.architecture
        self.endpoints = brain.endpoints
        self.database_entities = brain.database_entities
        self.symbols = [c["name"] for c in self.classes]

        _IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
        self._valid_identifier = lambda name: bool(name) and bool(_IDENT_RE.match(name))

    def plan(self) -> DocumentationTree:
        """Main planning entry point: builds complete adaptive DocumentationTree."""
        # 1. Build repository profile from evidence
        repo_profile = self._build_repository_profile()

        # 2. Detect capabilities
        capabilities = self._detect_capabilities(repo_profile)

        # 3. Plan pages
        pages = self._plan_pages(repo_profile, capabilities)

        # 4. Plan evidence-derived domain clusters (DeepWiki-style feature hierarchy)
        pages.extend(self._plan_domain_clusters())

        # 5. Build evidence scopes for each page
        for page in pages:
            page.evidence_scope = self._build_evidence_scope(page, repo_profile)

        # 6. Generate evidence-grounded purpose statements
        for page in pages:
            page.purpose = self._generate_purpose(page, repo_profile)

        # 7. Create documentation tree
        tree = DocumentationTree(
            repository_id=self.profile.get("project_name", Path(self.repo_path).name),
            analysis_run_id=self.analysis_run_id,
            commit_hash=self._get_commit_hash(),
            repository_profile=repo_profile,
            pages=pages,
        )

        return tree

    # ------------------------------------------------------------------
    # Domain clustering: DeepWiki-style parent/child feature pages derived
    # purely from directory + symbol evidence (no hardcoded domain names).
    # ------------------------------------------------------------------

    GENERIC_DIR_SEGMENTS = {
        "src", "app", "components", "component", "lib", "utils", "util",
        "data", "hooks", "services", "api", "routes", "pages", "views",
        "models", "test", "tests", "main", "java", "resources", "static",
        "public", "config", "core", "common", "shared", "types",
    }

    MAX_CLUSTER_CHILDREN = 6

    def _plan_domain_clusters(self) -> List[DocumentationPage]:
        """Groups production symbols by their most specific directory segment.

        A cluster page is created only when >=2 non-test symbols share a
        meaningful directory (e.g. src/components/effects -> "Effects").
        Each significant symbol inside becomes a child page.
        """
        prod_classes = [
            c for c in self.classes
            if not c.get("is_test")
            and self._valid_identifier(c.get("name", ""))
        ]

        clusters: Dict[str, List[Dict[str, Any]]] = {}
        for c in prod_classes:
            file_path = (c.get("file") or "").replace("\\", "/")
            dir_parts = [p for p in file_path.split("/")[:-1] if p]
            segment = None
            for part in reversed(dir_parts):
                if part.lower() not in self.GENERIC_DIR_SEGMENTS:
                    segment = part
                    break
            if segment is None:
                continue
            clusters.setdefault(segment, []).append(c)

        pages: List[DocumentationPage] = []
        order = 40

        for segment, cls_list in sorted(
            clusters.items(), key=lambda kv: (-len(kv[1]), kv[0])
        ):
            if len(cls_list) < 2:
                continue  # a lone symbol does not justify a cluster page

            cluster_id = f"domain-{self._slugify(segment)}"
            cluster_page = DocumentationPage(
                id=cluster_id,
                title=self._humanize_segment(segment),
                slug=cluster_id,
                order=order,
                page_type=PageType.FEATURES,
                is_mandatory=False,
            )
            pages.append(cluster_page)
            order += 1

            # Child pages for the most substantial symbols in this cluster.
            # Skip type-level noise (interfaces, Props types) — those belong in
            # the cluster page body, not as standalone wiki pages.
            ranked = sorted(
                cls_list,
                key=lambda c: (-len(c.get("methods", []) or []), c.get("name", "")),
            )
            child_order = 0
            seen_names = set()
            for cls in ranked:
                name = cls.get("name", "")
                if not name or name in seen_names:
                    continue
                if not self._valid_identifier(name):
                    continue
                if name.endswith(("Props", "PropsType")) :
                    continue
                if cls.get("stereotype") in ("Interface", "TypeAlias"):
                    continue
                seen_names.add(name)
                child_page = DocumentationPage(
                    id=f"symbol-{self._slugify(name)}",
                    title=name,
                    slug=f"symbol-{self._slugify(name)}",
                    parent_id=cluster_id,
                    order=child_order,
                    page_type=PageType.FEATURES,
                    is_mandatory=False,
                )
                pages.append(child_page)
                child_order += 1
                if child_order >= self.MAX_CLUSTER_CHILDREN:
                    break

        return pages

    @staticmethod
    def _slugify(text: str) -> str:
        return "".join(ch if ch.isalnum() else "-" for ch in text.lower()).strip("-")

    def _citations_for(self, symbol_names: List[str], limit: int = 20) -> List[str]:
        """Builds file#Lstart-Lend citation strings for the given symbols."""
        citations = []
        for sym_name in symbol_names[:limit]:
            cls = next((c for c in self.classes if c.get("name") == sym_name), None)
            if cls and cls.get("file") and cls.get("line_start"):
                end = cls.get("line_end", cls["line_start"] + 10)
                citations.append(f"{cls['file']}#L{cls['line_start']}-{end}")
        return citations

    @staticmethod
    def _humanize_segment(segment: str) -> str:
        """'effects' -> 'Effects', 'sp-dev' -> 'Sp Dev'. Evidence-derived naming only."""
        words = segment.replace("-", " ").replace("_", " ").split()
        return " ".join(w.capitalize() for w in words) if words else segment.capitalize()

    def _generate_purpose(self, page: DocumentationPage,
                          profile: RepositoryProfile) -> str:
        """Builds an evidence-grounded purpose statement from the page's scope.

        Purposes enumerate real files/symbols only — never invented domains.
        """
        scope = page.evidence_scope
        symbols = scope.relevant_symbols if scope else []
        files = scope.relevant_files if scope else []
        stats = profile.evidence_summary or {}

        def _sym_list(items, n=4):
            shown = ", ".join(items[:n])
            extra = len(items) - n
            return shown + (f" and {extra} more" if extra > 0 else "")

        if page.parent_id is not None and page.page_type == PageType.FEATURES:
            # Child symbol page
            cls = next((c for c in self.classes if c.get("name") == page.title), None)
            if cls:
                return (
                    f"Documents {cls['name']} ({cls.get('stereotype', 'module')}) defined "
                    f"in {cls.get('file', 'unknown source')} at lines "
                    f"{cls.get('line_start', '?')}-{cls.get('line_end', '?')}."
                )
            return f"Documents the {page.title} module."

        if page.id.startswith("domain-"):
            return (
                f"Covers the {page.title} subsystem: {_sym_list(symbols)} "
                f"— derived from AST analysis of {len(files)} source file(s)."
            )

        pt = page.page_type
        if pt == PageType.OVERVIEW:
            langs = ", ".join(profile.languages) or "unknown languages"
            fw = ", ".join(profile.frameworks) if profile.frameworks else "no framework detected"
            return (
                f"High-level introduction to {profile.repository_id}: tech stack ({langs}; {fw}), "
                f"repository statistics ({stats.get('total_classes', 0)} structural units), major "
                f"subsystems, entry points, and links to all sections of this wiki."
            )
        if pt == PageType.GETTING_STARTED:
            return (
                f"Setup and run instructions derived from actual repository manifests "
                f"({_sym_list(files, 5) if files else 'none detected'}). Covers prerequisites, "
                f"installation, environment setup, build, test, and run commands — never invented."
            )
        if pt == PageType.PROJECT_STRUCTURE:
            return (
                f"Directory layout walkthrough across {len(files)} source files, explaining the "
                f"responsibility of each top-level folder based on the symbols it contains."
            )
        if pt == PageType.CORE_ARCHITECTURE:
            return (
                f"Overview of how the major components ({_sym_list(symbols)}) relate, including "
                f"detected architectural style '{(self.architecture or {}).get('architectural_style', 'undetermined')}' "
                f"and component dependency relationships."
            )
        if pt == PageType.COMPONENTS:
            return f"Catalog of {_sym_list(symbols)} and other UI/component-layer modules with their relationships."
        if pt == PageType.FEATURES:
            caps = [c.get("capability") for c in self.capabilities if isinstance(c, dict)]
            return (
                f"Feature/domain pages discovered from package structure: "
                f"{_sym_list([c for c in caps if c], 5) if caps else 'single cohesive module'}."
            )
        if pt == PageType.DATA_LAYER:
            return f"Entities and data-access modules ({_sym_list(symbols)}) with their persistence relationships."
        if pt == PageType.API_ROUTES:
            eps = self.endpoints or []
            ep_summary = ", ".join(f"{e.get('route', '?')}" for e in eps[:5]) if eps else "no routes detected"
            return f"HTTP endpoints exposed by this repository ({ep_summary}) mapped to their handler symbols."
        if pt == PageType.STATE_MANAGEMENT:
            return f"Global state providers ({_sym_list(symbols)}): context definitions, state shape, and update flow."
        if pt == PageType.DEPENDENCIES:
            return f"External dependencies declared in {_sym_list(files, 3)}, grouped by production vs development use."
        if pt == PageType.CONFIGURATION:
            return f"Configuration files ({_sym_list(files, 4)}): keys, purposes, and secret-handling notes. Secret values are never displayed."
        if pt == PageType.TESTING:
            tests = [
                c["name"] for c in self.classes
                if c.get("is_test") or "Test" in c.get("name", "")
            ]
            return f"Test suite covering {len(tests)} test module(s) ({_sym_list(tests, 4)}). No coverage claims without coverage data."
        if pt == PageType.SECURITY:
            return f"Security-relevant code paths ({_sym_list(symbols)}): authentication, validation, and secret handling actually present in the source."
        if pt == PageType.INFRASTRUCTURE:
            return f"Infrastructure configuration found in {_sym_list(files, 4)} (Docker, CI pipelines)."
        if pt == PageType.DEPLOYMENT:
            return f"Deployment configuration from {_sym_list(files, 4)} — environments and rollout steps that are statically verifiable."
        if pt == PageType.GIT_HISTORY:
            return "Commit history, contributors, and change hotspots extracted from available Git metadata via GitMemory."
        if pt == PageType.RUNTIME_FLOW:
            flows = [f.get("flow_name") for f in self.flows if isinstance(f, dict)]
            return f"Execution flows detected from call/dependency structure: {_sym_list([f for f in flows if f], 3)}."
        if pt == PageType.DOMAIN_ARCHITECTURE:
            return f"Domain boundaries derived from package namespaces and dependency graph clustering."
        if pt == PageType.GLOSSARY:
            return f"Definitions of key repository terms ({_sym_list(symbols, 6)}) with source-file pointers."

        return f"Covers {_sym_list(symbols) if symbols else 'this area'} based on indexed repository evidence."

    def _build_repository_profile(self) -> RepositoryProfile:
        """Builds RepositoryProfile from actual RepositoryBrain evidence."""
        languages = []
        frameworks = []
        package_managers = []

        # Detect from brain profile
        primary_lang = self.profile.get("primary_language", "Unknown")
        framework = self.profile.get("framework", "")
        if primary_lang and primary_lang != "Unknown":
            languages.append(primary_lang)
        if framework:
            frameworks.append(framework)

        # Language honesty: derive from actually-parsed symbol languages when the
        # profiler was ambiguous (e.g. "Polyglot" for a repo with no manifests).
        lang_counts: Dict[str, int] = {}
        for c in self.classes:
            lang = (c.get("language") or "").lower()
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        if lang_counts:
            dominant = max(lang_counts, key=lang_counts.get)
            pretty = {
                "typescript": "TypeScript",
                "javascript": "JavaScript",
                "java": "Java",
                "python": "Python",
                "go": "Go",
                "rust": "Rust",
                "csharp": "C#",
                "cpp": "C++",
                "c": "C",
            }.get(dominant, dominant.capitalize())
            ambiguous = ("unknown", "polyglot")
            if not languages or languages[0].lower() in ambiguous:
                languages = [pretty]
            elif dominant.startswith(languages[0].split("/")[0].lower()) is False and len(lang_counts) == 1:
                languages = [pretty]

        repo_path = Path(self.repo_path)

        # Framework honesty: only keep framework claims backed by a manifest.
        manifest_evidence = {
            "Express/Next.js": (repo_path / "package.json").exists(),
            "Spring Boot": (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists(),
            "FastAPI/Flask": any(
                (repo_path / f).exists()
                for f in ("requirements.txt", "pyproject.toml", "Pipfile")
            ),
        }
        if frameworks:
            claim = frameworks[0]
            supported = None
            for key, ok in manifest_evidence.items():
                if key.lower() in claim.lower() and ok:
                    supported = True
                    break
                if key.lower() in claim.lower() and not ok:
                    supported = False
            if supported is False:
                # Downgrade to language-only identity; do not fabricate a framework
                frameworks = []

        # Detect package managers from repo path
        if (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists():
            package_managers.append("Maven" if (repo_path / "pom.xml").exists() else "Gradle")
        if (repo_path / "package.json").exists():
            package_managers.append("npm")
        if (repo_path / "requirements.txt").exists() or (repo_path / "pyproject.toml").exists():
            package_managers.append("pip")

        # Detect capabilities from actual evidence
        has_frontend = any(lang.lower() in ("typescript", "javascript") for lang in languages) or \
                       any(c.get("stereotype") in ("Component", "Page", "View") for c in self.classes)
        has_backend = any(c.get("stereotype") in ("Controller", "Service", "Repository") for c in self.classes)
        has_api = len(self.endpoints) > 0
        has_database = len(self.database_entities) > 0
        has_tests = any(c.get("is_test", False) or "Test" in c.get("name", "") for c in self.classes)
        has_docker = (repo_path / "Dockerfile").exists() or (repo_path / "docker-compose.yml").exists()
        has_ci = any((repo_path / d).exists() for d in [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci"])
        has_git = (repo_path / ".git").exists()
        has_state_management = any(c.get("stereotype") in ("Context", "Provider", "Store", "State") for c in self.classes)
        has_security_relevant_code = any(
            any(kw in str(c).lower() for kw in ("auth", "security", "jwt", "password", "secret", "token", "oauth", "cors", "csrf"))
            for c in self.classes
        )

        # Count endpoints
        endpoints_count = sum(len(c.get("endpoints", [])) for c in self.classes)

        # Build capabilities list
        capabilities = []
        if (repo_path / "README.md").exists() or (repo_path / "readme.md").exists():
            capabilities.append(CapabilityFlag.HAS_README)
        if package_managers:
            capabilities.append(CapabilityFlag.HAS_PACKAGE_MANAGER)
        if has_api:
            capabilities.append(CapabilityFlag.HAS_API)
        if has_database:
            capabilities.append(CapabilityFlag.HAS_DATABASE)
        if has_tests:
            capabilities.append(CapabilityFlag.HAS_TESTS)
        if has_docker:
            capabilities.append(CapabilityFlag.HAS_DOCKER)
        if has_ci:
            capabilities.append(CapabilityFlag.HAS_CI)
        if has_frontend:
            capabilities.append(CapabilityFlag.HAS_FRONTEND)
        if has_backend:
            capabilities.append(CapabilityFlag.HAS_BACKEND)
        if any(c.get("stereotype") == "Component" for c in self.classes):
            capabilities.append(CapabilityFlag.HAS_COMPONENTS)
        if has_api:
            capabilities.append(CapabilityFlag.HAS_ROUTES)
        if has_state_management:
            capabilities.append(CapabilityFlag.HAS_STATE_MANAGEMENT)
        if (repo_path / "package.json").exists() or (repo_path / "tsconfig.json").exists() or (repo_path / "pom.xml").exists():
            capabilities.append(CapabilityFlag.HAS_CONFIGURATION)
        if has_git:
            capabilities.append(CapabilityFlag.HAS_GIT_HISTORY)
        if has_security_relevant_code:
            capabilities.append(CapabilityFlag.HAS_SECURITY_RELEVANT_CODE)
        if self.capabilities:
            capabilities.append(CapabilityFlag.HAS_DOMAIN_FEATURES)

        return RepositoryProfile(
            repository_id=self.profile.get("project_name", Path(self.repo_path).name),
            analysis_run_id=self.analysis_run_id,
            languages=languages,
            frameworks=frameworks,
            package_managers=package_managers,
            has_frontend=has_frontend,
            has_backend=has_backend,
            has_api=has_api,
            has_database=has_database,
            has_tests=has_tests,
            has_docker=has_docker,
            has_ci=has_ci,
            has_git=has_git,
            has_state_management=has_state_management,
            has_security_relevant_code=has_security_relevant_code,
            symbols_count=len(self.symbols),
            relationships_count=len(self.brain.symbols),  # placeholder - actual count from graph
            files_count=len(set(c.get("file", "") for c in self.classes if c.get("file"))),
            endpoints_count=endpoints_count,
            capabilities=capabilities,
            evidence_summary={
                "total_classes": len(self.classes),
                "total_endpoints": endpoints_count,
                "controllers": len([c for c in self.classes if c.get("stereotype") == "Controller"]),
                "services": len([c for c in self.classes if c.get("stereotype") == "Service"]),
                "repositories": len([c for c in self.classes if c.get("stereotype") == "Repository"]),
                "entities": len([c for c in self.classes if c.get("stereotype") in ("Entity", "Model")]),
                "components": len([c for c in self.classes if c.get("stereotype") == "Component"]),
                "contexts": len([c for c in self.classes if c.get("stereotype") == "Context"]),
            }
        )

    def _detect_capabilities(self, profile: RepositoryProfile) -> List[CapabilityFlag]:
        """Returns capability flags from repository profile."""
        return profile.capabilities

    def _plan_pages(self, profile: RepositoryProfile, capabilities: List[CapabilityFlag]) -> List[DocumentationPage]:
        """Plans adaptive documentation pages based on evidence."""
        pages = []
        order = 0

        # Always add mandatory pages
        for page_type in self.MANDATORY_PAGES:
            meta = self.PAGE_TYPE_METADATA[page_type]
            page = DocumentationPage(
                id=page_type.value,
                title=meta["title"],
                slug=page_type.value,
                order=order,
                page_type=page_type,
                is_mandatory=meta.get("is_mandatory", False),
            )
            pages.append(page)
            order += 1

        # Conditionally add pages based on evidence
        conditional_order = 10
        for page_type in self.CONDITIONAL_PAGES:
            if self._should_include_page(page_type, profile, capabilities):
                meta = self.PAGE_TYPE_METADATA[page_type]
                page = DocumentationPage(
                    id=page_type.value,
                    title=meta["title"],
                    slug=page_type.value,
                    order=conditional_order,
                    page_type=page_type,
                    is_mandatory=False,
                )
                pages.append(page)
                conditional_order += 1

        # Add sub-sections for each page
        for page in pages:
            page.sections = self._plan_sections(page, profile)

        return pages

    def _should_include_page(self, page_type: PageType, profile: RepositoryProfile, capabilities: List[CapabilityFlag]) -> bool:
        """Determines if a conditional page should be included based on evidence."""
        if page_type == PageType.COMPONENTS:
            # Require at least 2 components or a component + context for meaningful component architecture
            return profile.evidence_summary.get("components", 0) >= 2 or \
                   (profile.evidence_summary.get("components", 0) >= 1 and profile.evidence_summary.get("contexts", 0) >= 1)
        elif page_type == PageType.FEATURES:
            # Require at least 2 capabilities or meaningful domain features
            return len(self.capabilities) >= 2
        elif page_type == PageType.DATA_LAYER:
            return profile.has_database or profile.evidence_summary.get("entities", 0) > 0 or \
                   profile.evidence_summary.get("repositories", 0) > 0
        elif page_type == PageType.API_ROUTES:
            return profile.has_api
        elif page_type == PageType.STATE_MANAGEMENT:
            return profile.has_state_management
        elif page_type == PageType.DEPENDENCIES:
            return CapabilityFlag.HAS_PACKAGE_MANAGER in capabilities
        elif page_type == PageType.CONFIGURATION:
            return CapabilityFlag.HAS_CONFIGURATION in capabilities
        elif page_type == PageType.TESTING:
            return profile.has_tests
        elif page_type == PageType.SECURITY:
            return profile.has_security_relevant_code
        elif page_type == PageType.INFRASTRUCTURE:
            return profile.has_docker or profile.has_ci
        elif page_type == PageType.DEPLOYMENT:
            return profile.has_docker or profile.has_ci
        elif page_type == PageType.GIT_HISTORY:
            return profile.has_git
        elif page_type == PageType.RUNTIME_FLOW:
            return len(self.flows) > 0
        elif page_type == PageType.DOMAIN_ARCHITECTURE:
            return len(self.capabilities) > 0 and len(self.classes) > 10
        return False

    def _plan_sections(self, page: DocumentationPage, profile: RepositoryProfile) -> List[DocumentationSection]:
        """Plans sections for a specific page."""
        sections = []

        if page.page_type == PageType.OVERVIEW:
            sections = [
                DocumentationSection(id="summary", title="Repository Summary", order=0),
                DocumentationSection(id="tech-stack", title="Technology Stack", order=1),
                DocumentationSection(id="statistics", title="Repository Statistics", order=2),
                DocumentationSection(id="architecture", title="Architecture Overview", order=3),
                DocumentationSection(id="major-features", title="Major Features", order=4),
                DocumentationSection(id="entry-points", title="Entry Points", order=5),
                DocumentationSection(id="important-files", title="Important Files", order=6),
                DocumentationSection(id="related-pages", title="Related Documentation", order=7),
            ]
        elif page.page_type == PageType.GETTING_STARTED:
            sections = [
                DocumentationSection(id="prerequisites", title="Prerequisites", order=0),
                DocumentationSection(id="installation", title="Installation", order=1),
                DocumentationSection(id="environment", title="Environment Setup", order=2),
                DocumentationSection(id="dev-commands", title="Development Commands", order=3),
                DocumentationSection(id="build-commands", title="Build Commands", order=4),
                DocumentationSection(id="test-commands", title="Test Commands", order=5),
                DocumentationSection(id="run-commands", title="Run Commands", order=6),
            ]
        elif page.page_type == PageType.PROJECT_STRUCTURE:
            sections = [
                DocumentationSection(id="tree", title="Project Tree", order=0),
                DocumentationSection(id="directories", title="Directory Responsibilities", order=1),
                DocumentationSection(id="important-files", title="Important Files", order=2),
            ]
        elif page.page_type == PageType.CORE_ARCHITECTURE:
            sections = [
                DocumentationSection(id="system-architecture", title="System Architecture", order=0),
                DocumentationSection(id="layer-boundaries", title="Layer Boundaries", order=1),
                DocumentationSection(id="component-relationships", title="Component Relationships", order=2),
                DocumentationSection(id="data-flow", title="Data Flow", order=3),
            ]
        elif page.page_type == PageType.COMPONENTS:
            sections = [
                DocumentationSection(id="component-list", title="Component Catalog", order=0),
                DocumentationSection(id="component-hierarchy", title="Component Hierarchy", order=1),
                DocumentationSection(id="shared-components", title="Shared Components", order=2),
            ]
        elif page.page_type == PageType.FEATURES:
            sections = [
                DocumentationSection(id="feature-list", title="Feature Catalog", order=0),
                DocumentationSection(id="feature-details", title="Feature Details", order=1),
            ]
        elif page.page_type == PageType.DATA_LAYER:
            sections = [
                DocumentationSection(id="entities", title="Entities & Models", order=0),
                DocumentationSection(id="repositories", title="Repositories & Data Access", order=1),
                DocumentationSection(id="migrations", title="Migrations & Schema", order=2),
            ]
        elif page.page_type == PageType.API_ROUTES:
            sections = [
                DocumentationSection(id="rest-endpoints", title="REST Endpoints", order=0),
                DocumentationSection(id="api-handlers", title="API Handlers", order=1),
                DocumentationSection(id="middleware", title="Middleware & Guards", order=2),
            ]
        elif page.page_type == PageType.STATE_MANAGEMENT:
            sections = [
                DocumentationSection(id="state-providers", title="State Providers", order=0),
                DocumentationSection(id="global-state", title="Global State", order=1),
                DocumentationSection(id="state-flow", title="State Flow", order=2),
            ]
        elif page.page_type == PageType.DEPENDENCIES:
            sections = [
                DocumentationSection(id="production", title="Production Dependencies", order=0),
                DocumentationSection(id="development", title="Development Dependencies", order=1),
                DocumentationSection(id="internal", title="Internal Modules", order=2),
            ]
        elif page.page_type == PageType.CONFIGURATION:
            sections = [
                DocumentationSection(id="env-config", title="Environment Configuration", order=0),
                DocumentationSection(id="build-config", title="Build Configuration", order=1),
                DocumentationSection(id="runtime-config", title="Runtime Configuration", order=2),
            ]
        elif page.page_type == PageType.TESTING:
            sections = [
                DocumentationSection(id="test-framework", title="Test Framework", order=0),
                DocumentationSection(id="test-structure", title="Test Structure", order=1),
                DocumentationSection(id="test-coverage", title="Coverage Areas", order=2),
            ]
        elif page.page_type == PageType.SECURITY:
            sections = [
                DocumentationSection(id="auth", title="Authentication", order=0),
                DocumentationSection(id="authorization", title="Authorization", order=1),
                DocumentationSection(id="validation", title="Input Validation", order=2),
                DocumentationSection(id="secrets", title="Secrets Management", order=3),
            ]
        elif page.page_type == PageType.INFRASTRUCTURE:
            sections = [
                DocumentationSection(id="docker", title="Docker Configuration", order=0),
                DocumentationSection(id="ci-cd", title="CI/CD Pipelines", order=1),
                DocumentationSection(id="monitoring", title="Monitoring & Observability", order=2),
            ]
        elif page.page_type == PageType.DEPLOYMENT:
            sections = [
                DocumentationSection(id="deploy-config", title="Deployment Configuration", order=0),
                DocumentationSection(id="environments", title="Environments", order=1),
                DocumentationSection(id="rollout", title="Rollout Strategy", order=2),
            ]
        elif page.page_type == PageType.GIT_HISTORY:
            sections = [
                DocumentationSection(id="commit-history", title="Commit History", order=0),
                DocumentationSection(id="contributors", title="Contributors", order=1),
                DocumentationSection(id="hotspots", title="Change Hotspots", order=2),
            ]
        elif page.page_type == PageType.RUNTIME_FLOW:
            sections = [
                DocumentationSection(id="execution-flows", title="Execution Flows", order=0),
                DocumentationSection(id="request-lifecycle", title="Request Lifecycle", order=1),
                DocumentationSection(id="async-flows", title="Async Flows", order=2),
            ]
        elif page.page_type == PageType.DOMAIN_ARCHITECTURE:
            sections = [
                DocumentationSection(id="domains", title="Domain Boundaries", order=0),
                DocumentationSection(id="domain-models", title="Domain Models", order=1),
                DocumentationSection(id="domain-services", title="Domain Services", order=2),
            ]
        elif page.page_type == PageType.GLOSSARY:
            sections = [
                DocumentationSection(id="glossary-entries", title="Glossary Entries", order=0),
            ]

        return sections

    def _build_evidence_scope(self, page: DocumentationPage, profile: RepositoryProfile) -> PageEvidenceScope:
        """Builds bounded evidence scope for a page from actual repository evidence."""
        relevant_files = []
        relevant_symbols = []
        relevant_relationships = []
        evidence_ids = []
        related_pages = []

        # Domain-cluster pages (domain-<segment>) scope to all symbols in that directory
        if page.id.startswith("domain-"):
            segment = page.id[len("domain-"):].replace("-", "_")
            alt_segment = page.id[len("domain-"):].replace("-", "-")
            members = []
            for c in self.classes:
                if c.get("is_test"):
                    continue
                file_path = (c.get("file") or "").replace("\\", "/")
                dir_parts = [p for p in file_path.split("/")[:-1] if p]
                deepest = None
                for part in reversed(dir_parts):
                    if part.lower() not in self.GENERIC_DIR_SEGMENTS:
                        deepest = part
                        break
                if deepest is not None and (
                    deepest.lower().replace("-", "_") == segment.lower()
                    or self._slugify(deepest) == alt_segment
                ):
                    members.append(c)
            relevant_symbols = [c["name"] for c in members]
            relevant_files = list(dict.fromkeys(c.get("file", "") for c in members if c.get("file")))
            return PageEvidenceScope(
                page_id=page.id,
                relevant_files=relevant_files,
                relevant_symbols=relevant_symbols,
                evidence_ids=self._citations_for(relevant_symbols),
            )

        # Symbol child pages scope to exactly one class
        if page.id.startswith("symbol-"):
            cls = next((c for c in self.classes if self._slugify(c.get("name", "")) == page.id[len("symbol-"):]), None)
            if cls is not None:
                sym = [cls["name"]]
                files = [cls["file"]] if cls.get("file") else []
                rel_pages = []
                # link back to owning domain cluster, if planned
                return PageEvidenceScope(
                    page_id=page.id,
                    relevant_files=files,
                    relevant_symbols=sym,
                    evidence_ids=self._citations_for(sym),
                    related_pages=rel_pages,
                )
            return PageEvidenceScope(page_id=page.id)

        # Collect evidence based on page type
        if page.page_type == PageType.OVERVIEW:
            # All important symbols and files
            important_classes = [c for c in self.classes if not c.get("is_test") and c.get("stereotype") in 
                               ("Controller", "Service", "Repository", "Entity", "Component", "Context", "Configuration")]
            relevant_symbols = [c["name"] for c in important_classes[:20]]
            relevant_files = list(dict.fromkeys([c.get("file", "") for c in important_classes if c.get("file")]))
            # Fallback: repos without framework stereotypes still deserve a real overview
            if not important_classes:
                prod = [c for c in self.classes if not c.get("is_test")]
                relevant_symbols = [c["name"] for c in prod[:20]]
                relevant_files = list(dict.fromkeys([c.get("file", "") for c in prod if c.get("file")]))

        elif page.page_type == PageType.GETTING_STARTED:
            # README, package files, docker, CI
            repo_path = Path(self.repo_path)
            for f in ["README.md", "readme.md", "package.json", "pom.xml", "build.gradle", "requirements.txt", 
                      "pyproject.toml", "Dockerfile", "docker-compose.yml", ".env.example"]:
                if (repo_path / f).exists():
                    relevant_files.append(f)

        elif page.page_type == PageType.PROJECT_STRUCTURE:
            # All source files
            all_files = [c.get("file", "") for c in self.classes if c.get("file")]
            relevant_files = list(dict.fromkeys(all_files))

        elif page.page_type == PageType.CORE_ARCHITECTURE:
            # Architectural symbols
            arch_symbols = [c for c in self.classes if c.get("stereotype") in 
                          ("Controller", "Service", "Repository", "Entity", "Component", "Context", "Configuration")]
            relevant_symbols = [c["name"] for c in arch_symbols]
            relevant_files = list(dict.fromkeys([c.get("file", "") for c in arch_symbols if c.get("file")]))
            # Fallback for repos without framework stereotypes
            if not arch_symbols:
                prod = [c for c in self.classes if not c.get("is_test")]
                relevant_symbols = [c["name"] for c in prod[:20]]
                relevant_files = list(dict.fromkeys([c.get("file", "") for c in prod if c.get("file")]))

        elif page.page_type == PageType.COMPONENTS:
            comps = [c for c in self.classes if c.get("stereotype") in ("Component", "Context", "Provider", "Page", "View")]
            relevant_symbols = [c["name"] for c in comps]
            relevant_files = list(dict.fromkeys([c.get("file", "") for c in comps if c.get("file")]))

        elif page.page_type == PageType.FEATURES:
            for cap in self.capabilities:
                if isinstance(cap, dict) and "components" in cap:
                    relevant_symbols.extend(cap["components"][:5])
                    if "evidence_sources" in cap:
                        relevant_files.extend(cap["evidence_sources"])

        elif page.page_type == PageType.DATA_LAYER:
            data_symbols = [c for c in self.classes if c.get("stereotype") in ("Entity", "Model", "Repository")]
            relevant_symbols = [c["name"] for c in data_symbols]
            relevant_files = list(dict.fromkeys([c.get("file", "") for c in data_symbols if c.get("file")]))

        elif page.page_type == PageType.API_ROUTES:
            controllers = [c for c in self.classes if c.get("stereotype") == "Controller"]
            relevant_symbols = [c["name"] for c in controllers]
            relevant_files = list(dict.fromkeys([c.get("file", "") for c in controllers if c.get("file")]))
            for ep in self.endpoints:
                if ep.get("handler"):
                    relevant_symbols.append(ep["handler"])

        elif page.page_type == PageType.STATE_MANAGEMENT:
            state_symbols = [c for c in self.classes if c.get("stereotype") in ("Context", "Provider", "Store", "State")]
            relevant_symbols = [c["name"] for c in state_symbols]
            relevant_files = list(dict.fromkeys([c.get("file", "") for c in state_symbols if c.get("file")]))

        elif page.page_type == PageType.DEPENDENCIES:
            # Package files
            repo_path = Path(self.repo_path)
            for f in ["package.json", "pom.xml", "build.gradle", "requirements.txt", "pyproject.toml", "go.mod"]:
                if (repo_path / f).exists():
                    relevant_files.append(f)

        elif page.page_type == PageType.CONFIGURATION:
            repo_path = Path(self.repo_path)
            for f in [".env.example", "tsconfig.json", "next.config.ts", "vite.config.ts", "application.properties",
                      "application.yml", "pom.xml", "build.gradle", "package.json"]:
                if (repo_path / f).exists():
                    relevant_files.append(f)

        elif page.page_type == PageType.TESTING:
            test_classes = [c for c in self.classes if c.get("is_test") or "Test" in c.get("name", "")]
            relevant_symbols = [c["name"] for c in test_classes]
            relevant_files = list(dict.fromkeys([c.get("file", "") for c in test_classes if c.get("file")]))

        elif page.page_type == PageType.SECURITY:
            # Files with security-relevant code
            for c in self.classes:
                content = str(c).lower()
                if any(kw in content for kw in ("auth", "security", "jwt", "password", "secret", "token", "oauth", "cors", "csrf")):
                    relevant_symbols.append(c["name"])
                    if c.get("file"):
                        relevant_files.append(c["file"])

        elif page.page_type == PageType.INFRASTRUCTURE:
            repo_path = Path(self.repo_path)
            for f in ["Dockerfile", "docker-compose.yml", ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile"]:
                if (repo_path / f).exists():
                    relevant_files.append(f)

        elif page.page_type == PageType.DEPLOYMENT:
            repo_path = Path(self.repo_path)
            for f in ["Dockerfile", "docker-compose.yml", "k8s", "helm", "terraform", ".github/workflows"]:
                if (repo_path / f).exists():
                    relevant_files.append(f)

        elif page.page_type == PageType.GIT_HISTORY:
            # Git history evidence would come from GitMemory
            pass

        elif page.page_type == PageType.RUNTIME_FLOW:
            for flow in self.flows:
                if isinstance(flow, dict) and "participating_components" in flow:
                    relevant_symbols.extend(flow["participating_components"])

        elif page.page_type == PageType.DOMAIN_ARCHITECTURE:
            for cap in self.capabilities:
                if isinstance(cap, dict) and "components" in cap:
                    relevant_symbols.extend(cap["components"])

        elif page.page_type == PageType.GLOSSARY:
            # Important symbols across the repository
            important = [c for c in self.classes if not c.get("is_test") and c.get("stereotype") in 
                        ("Controller", "Service", "Repository", "Entity", "Component", "Context", "Configuration",
                         "Interface", "Model", "RouteHandler")]
            # Fallback: repos without framework stereotypes still get real glossary terms
            if not important:
                important = [c for c in self.classes
                             if not c.get("is_test") and self._valid_identifier(c.get("name", ""))]
            relevant_symbols = [c["name"] for c in important[:30]]

        # Deduplicate
        relevant_files = list(dict.fromkeys([f for f in relevant_files if f]))
        relevant_symbols = list(dict.fromkeys(relevant_symbols))

        # Build evidence IDs (file#LineStart-LineEnd format)
        for sym_name in relevant_symbols[:20]:
            cls = next((c for c in self.classes if c.get("name") == sym_name), None)
            if cls and cls.get("file") and cls.get("line_start"):
                evidence_ids.append(f"{cls['file']}#L{cls['line_start']}-{cls.get('line_end', cls['line_start'] + 10)}")

        return PageEvidenceScope(
            page_id=page.id,
            relevant_files=relevant_files,
            relevant_symbols=relevant_symbols,
            relevant_relationships=relevant_relationships,
            evidence_ids=evidence_ids,
            related_pages=related_pages,
        )

    def _get_commit_hash(self) -> Optional[str]:
        """Gets current git commit hash if available."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()[:12]
        except Exception:
            pass
        return None


def plan_documentation(brain: RepositoryBrain) -> DocumentationTree:
    """Convenience function to plan documentation from RepositoryBrain."""
    planner = DocumentationPlanner(brain)
    return planner.plan()