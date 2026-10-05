"""
DevLensX Documentation Intelligence Core - Planning Models
Structured data models for adaptive documentation planning and evidence scoping.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class PageType(str, Enum):
    OVERVIEW = "overview"
    GETTING_STARTED = "getting_started"
    PROJECT_STRUCTURE = "project_structure"
    CORE_ARCHITECTURE = "core_architecture"
    COMPONENTS = "components"
    FEATURES = "features"
    DATA_LAYER = "data_layer"
    API_ROUTES = "api_routes"
    STATE_MANAGEMENT = "state_management"
    DEPENDENCIES = "dependencies"
    CONFIGURATION = "configuration"
    TESTING = "testing"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    DEPLOYMENT = "deployment"
    GIT_HISTORY = "git_history"
    RUNTIME_FLOW = "runtime_flow"
    DOMAIN_ARCHITECTURE = "domain_architecture"
    GLOSSARY = "glossary"


class CapabilityFlag(str, Enum):
    HAS_README = "has_readme"
    HAS_PACKAGE_MANAGER = "has_package_manager"
    HAS_API = "has_api"
    HAS_DATABASE = "has_database"
    HAS_TESTS = "has_tests"
    HAS_DOCKER = "has_docker"
    HAS_CI = "has_ci"
    HAS_FRONTEND = "has_frontend"
    HAS_BACKEND = "has_backend"
    HAS_COMPONENTS = "has_components"
    HAS_ROUTES = "has_routes"
    HAS_STATE_MANAGEMENT = "has_state_management"
    HAS_CONFIGURATION = "has_configuration"
    HAS_GIT_HISTORY = "has_git_history"
    HAS_SECURITY_RELEVANT_CODE = "has_security_relevant_code"
    HAS_DOMAIN_FEATURES = "has_domain_features"


@dataclass
class RepositoryProfile:
    """Repository profile derived from actual evidence."""
    repository_id: str
    analysis_run_id: str
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)
    
    has_frontend: bool = False
    has_backend: bool = False
    has_api: bool = False
    has_database: bool = False
    has_tests: bool = False
    has_docker: bool = False
    has_ci: bool = False
    has_git: bool = False
    has_state_management: bool = False
    has_security_relevant_code: bool = False
    
    symbols_count: int = 0
    relationships_count: int = 0
    files_count: int = 0
    endpoints_count: int = 0
    
    capabilities: List[CapabilityFlag] = field(default_factory=list)
    evidence_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageEvidenceScope:
    """Bounded evidence scope for a documentation page."""
    page_id: str
    relevant_files: List[str] = field(default_factory=list)
    relevant_symbols: List[str] = field(default_factory=list)
    relevant_relationships: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    related_pages: List[str] = field(default_factory=list)


@dataclass
class DocumentationSection:
    id: str
    title: str
    description: str = ""
    order: int = 0
    evidence_ids: List[str] = field(default_factory=list)
    child_section_ids: List[str] = field(default_factory=list)


@dataclass
class DocumentationPage:
    id: str
    title: str
    slug: str
    parent_id: Optional[str] = None
    order: int = 0
    page_type: PageType = PageType.COMPONENTS
    purpose: str = ""
    sections: List[DocumentationSection] = field(default_factory=list)
    evidence_scope: Optional[PageEvidenceScope] = None
    related_symbols: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    is_mandatory: bool = False


@dataclass
class DocumentationTree:
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str] = None
    repository_profile: Optional[RepositoryProfile] = None
    pages: List[DocumentationPage] = field(default_factory=list)

    def get_page(self, page_id: str) -> Optional[DocumentationPage]:
        for page in self.pages:
            if page.id == page_id:
                return page
        return None

    def get_children(self, parent_id: str) -> List[DocumentationPage]:
        return [p for p in self.pages if p.parent_id == parent_id]

    def get_root_pages(self) -> List[DocumentationPage]:
        return [p for p in self.pages if p.parent_id is None]

    def to_deepwiki_dict(self) -> Dict[str, Any]:
        """Serializes to the DeepWiki-compatible page-tree contract.

        Shape:
        {
          "repo_notes": [{"content": "..."}],
          "pages": [
            {"title": ..., "purpose": ..., "parent": <parent title or omitted>,
             "page_notes": [...], ...}
          ]
        }
        Parent references use titles (DeepWiki convention), resolved from page ids.
        """
        id_to_title = {p.id: p.title for p in self.pages}

        repo_note = ""
        if self.repository_profile is not None:
            rp = self.repository_profile
            langs = ", ".join(rp.languages) if rp.languages else "Unknown"
            frameworks = ", ".join(rp.frameworks) if rp.frameworks else "no framework detected"
            stats = rp.evidence_summary or {}
            total = stats.get("total_classes", rp.symbols_count)
            repo_note = (
                f"{self.repository_id} is a {langs} repository using {frameworks}, "
                f"containing {total} parsed structural units across "
                f"{rp.files_count} source files. "
                f"This wiki was generated deterministically from AST evidence "
                f"(analysis_run_id: {self.analysis_run_id}"
                + (f", commit: {self.commit_hash}" if self.commit_hash else "")
                + ")."
            )

        pages_out = []
        for page in sorted(self.pages, key=lambda p: (p.order, p.title)):
            entry = {
                "title": page.title,
                "purpose": page.purpose,
                "page_notes": [],
            }
            if page.parent_id and page.parent_id in id_to_title:
                entry["parent"] = id_to_title[page.parent_id]
            scope = page.evidence_scope
            if scope is not None:
                if scope.relevant_symbols:
                    entry["key_symbols"] = scope.relevant_symbols[:10]
                if scope.relevant_files:
                    entry["relevant_files"] = scope.relevant_files[:10]
            pages_out.append(entry)

        return {
            "repo_notes": [{"content": repo_note}],
            "pages": pages_out,
        }


@dataclass
class DocumentationCacheKey:
    repository_id: str
    analysis_run_id: str
    commit_hash: Optional[str] = None
    
    def to_string(self) -> str:
        return f"{self.repository_id}:{self.analysis_run_id}:{self.commit_hash or 'no-commit'}"