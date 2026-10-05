from devlensx.api.routes.auth import router as auth_router
from devlensx.api.routes.repositories import router as repositories_router
from devlensx.api.routes.copilot import router as copilot_router
from devlensx.api.routes.debug import router as debug_router
from devlensx.api.routes.git import router as git_router
from devlensx.api.routes.wiki import router as wiki_router
from devlensx.api.routes.evidence import router as evidence_router
from devlensx.api.routes.diagrams import router as diagrams_router
from devlensx.api.routes.chat import router as chat_router
from devlensx.api.routes.workspace import router as workspace_router
from devlensx.api.routes.incremental import router as incremental_router
from devlensx.api.routes.codemap import router as codemap_router
from devlensx.api.routes.codereview import router as codereview_router
from devlensx.api.routes.evaluation import router as evaluation_router
from devlensx.api.routes.governance import router as governance_router
from devlensx.api.routes.digest import router as digest_router
from devlensx.api.routes.ingest_routes import router as ingest_router, analyze_router

__all__ = [
    "auth_router",
    "repositories_router",
    "copilot_router",
    "debug_router",
    "git_router",
    "wiki_router",
    "evidence_router",
    "diagrams_router",
    "chat_router",
    "workspace_router",
    "incremental_router",
    "codemap_router",
    "codereview_router",
    "evaluation_router",
    "governance_router",
    "digest_router",
    "ingest_router",
    "analyze_router",
]