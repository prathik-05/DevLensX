"""
DevLensX Documentation Intelligence Subsystem
Adaptive, evidence-grounded documentation generation from RepositoryBrain.
"""

from devlensx.understanding.documentation.planner import (
    DocumentationPlanner,
    plan_documentation,
    DocumentationTree,
    DocumentationPage,
    DocumentationSection,
    PageEvidenceScope,
    RepositoryProfile,
    PageType,
    CapabilityFlag,
    DocumentationCacheKey,
)

from devlensx.understanding.documentation.page_generator import (
    PageGenerator,
    EvidenceContextBuilder,
    GeneratedPage,
    generate_documentation,
)

from devlensx.understanding.documentation.cache import (
    DocumentationCache,
    CacheEntry,
    get_documentation_cache,
    get_cached_documentation,
    cache_documentation,
)

__all__ = [
    # Planner
    "DocumentationPlanner",
    "plan_documentation",
    "DocumentationTree",
    "DocumentationPage",
    "DocumentationSection",
    "PageEvidenceScope",
    "RepositoryProfile",
    "PageType",
    "CapabilityFlag",
    "DocumentationCacheKey",
    # Page Generator
    "PageGenerator",
    "EvidenceContextBuilder",
    "GeneratedPage",
    "generate_documentation",
    # Cache
    "DocumentationCache",
    "CacheEntry",
    "get_documentation_cache",
    "get_cached_documentation",
    "cache_documentation",
]