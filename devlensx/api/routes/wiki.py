"""
DevLensX Living Wiki and Repository Understanding API Routes (D7 Extended)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from devlensx.understanding import WikiGenerator
from devlensx.evidence.resolver import get_snapshot_registry
from devlensx.documentation import (
    DocumentationPageGenerator,
    get_documentation_cache,
    DocumentationPage,
)

router = APIRouter(prefix="/api/wiki", tags=["Interactive Living Wiki"])


class WikiAskRequest(BaseModel):
    question: str
    page_id: Optional[str] = None
    section_id: Optional[str] = None


@router.get("/provider/status")
def get_wiki_provider_status():
    """Returns active AI reasoning provider and configuration health."""
    from devlensx.llm.provider import get_llm_provider
    try:
        provider = get_llm_provider("auto")
        if provider:
            caps = provider.capabilities()
            prov_name = provider.__class__.__name__.replace("Provider", "").lower()
            return {
                "status": "CONFIGURED",
                "provider": prov_name,
                "model": provider.model() or "default",
                "configured": True,
                "offline": bool(caps.get("offline", False)),
            }
    except Exception:
        pass
    return {
        "status": "OFFLINE_FALLBACK",
        "provider": "offline",
        "model": "deterministic_heuristics",
        "configured": False,
        "offline": True,
    }


# ---- Spec Wiki Engine (analysis_id page tree and single page) ----
# NOTE: These routes must be declared BEFORE generic /{analysis_id}
@router.get("/{analysis_id}/page/{page_id}")
def get_wiki_page_spec(analysis_id: str, page_id: str):
    """Spec: GET /api/wiki/{analysis_id}/page/{page_id} - single wiki page from devlensx/wiki.py cache."""
    try:
        from devlensx.wiki import get_wiki_page
        page = get_wiki_page(analysis_id, page_id)
        if page:
            return page
    except Exception:
        pass
    # Fallback to D7 documentation cache
    registry = get_snapshot_registry()
    snap = registry.get(analysis_id)
    if snap:
        cache = get_documentation_cache()
        p = cache.get_page(snap.repository_id, analysis_id, snap.commit_hash, page_id)
        if p:
            return p.to_dict()
    raise HTTPException(status_code=404, detail=f"Wiki page '{page_id}' not found for analysis '{analysis_id}'.")


@router.post("/{analysis_id}/ask")
def ask_wiki_copilot(analysis_id: str, req: WikiAskRequest):
    """Answers repository and wiki page questions with grounded AST and graph facts and citations."""
    from devlensx.reasoning.engine import RepositoryReasoningEngine
    from devlensx.api.main import global_state

    repo_model = global_state.get("repo_model") or {}
    graph_store = global_state.get("graph_store")
    retriever = global_state.get("retriever")

    engine = RepositoryReasoningEngine()
    question = req.question
    if req.page_id:
        question = f"[Context: Wiki Page '{req.page_id}'] {question}"

    result = engine.answer_repository_question(
        question=question,
        repo_model=repo_model,
        graph_store=graph_store,
        retriever=retriever,
    )
    return {
        "analysis_id": analysis_id,
        "page_id": req.page_id,
        "question": req.question,
        "answer": result.get("answer", ""),
        "citations": result.get("citations", []),
        "verdict": result.get("verdict", "VERIFIED_EVIDENCE"),
    }


@router.get("/{analysis_id}")
def get_wiki_tree_spec(analysis_id: str):
    """Spec: GET /api/wiki/{analysis_id} - page tree and content summary (devlensx/wiki.py)."""
    try:
        from devlensx.wiki import get_wiki_tree
        tree = get_wiki_tree(analysis_id)
        if tree:
            return tree
    except Exception:
        pass
    # Check D7 snapshot fallback: if snapshot exists, return D7 pages summary
    try:
        registry = get_snapshot_registry()
        snap = registry.get(analysis_id)
        if snap:
            cache = get_documentation_cache()
            pages = cache.list_pages(snap.repository_id, analysis_id, snap.commit_hash)
            if pages:
                return {
                    "analysis_id": analysis_id,
                    "repository_id": snap.repository_id,
                    "commit_hash": snap.commit_hash,
                    "page_tree": [{"id": p.id, "title": p.title, "type": "doc"} for p in pages],
                    "count": len(pages),
                    "pages_summary": {p.id: p.purpose for p in pages},
                }
    except Exception:
        pass
    raise HTTPException(status_code=404, detail=f"Wiki tree not found for analysis '{analysis_id}'. Run /api/analyze first.")


def get_living_wiki(repo_id: str = "default"):
    """Helper for legacy living wiki by repo_id."""
    from devlensx.api.main import global_state
    brain = global_state.get("brain")
    if brain is not None:
        return WikiGenerator.generate_living_wiki(brain.repo_path, brain.classes, brain=brain)
    repo_model = global_state.get("repo_model") or {}
    classes = repo_model.get("classes", [])
    repo_path = repo_model.get("repo_path", "eval_repos/spring-petclinic")
    return WikiGenerator.generate_living_wiki(repo_path, classes)


@router.get("")
def get_living_wiki_root():
    """Returns the living interactive Wiki (root)."""
    return get_living_wiki("default")


@router.get("/default/architecture")
def get_wiki_architecture_default():
    """Returns architectural style and detected pattern evidence (default/latest analysis)."""
    wiki = get_living_wiki("default")
    return wiki.get("architecture", {})


@router.get("/default/capabilities")
def get_wiki_capabilities_default():
    """Returns discovered business capabilities (default/latest analysis)."""
    wiki = get_living_wiki("default")
    return {"capabilities": wiki.get("capabilities", [])}


@router.get("/default/flows")
def get_wiki_flows_default():
    """Returns mapped execution flows (default/latest analysis)."""
    wiki = get_living_wiki("default")
    return {"user_flows": wiki.get("user_flows", [])}


# ----------------------------------------------------------------------
# D7 Verified Documentation Pages API
# ----------------------------------------------------------------------

@router.get("/{analysis_run_id}/pages")
def get_wiki_pages(analysis_run_id: str):
    """Returns catalog and list of verified documentation pages for an analysis run."""
    from devlensx.api.main import global_state
    registry = get_snapshot_registry()
    snapshot = registry.get(analysis_run_id)

    if not snapshot:
        repo_model = global_state.get("repo_model") or {}
        repo_id = repo_model.get("repository", "default")
    else:
        repo_id = snapshot.repository_id

    cache = get_documentation_cache()
    cached_pages = cache.list_pages(repo_id, analysis_run_id, snapshot.commit_hash if snapshot else None)

    if not cached_pages:
        repo_model = global_state.get("repo_model") or {}
        if snapshot:
            gen = DocumentationPageGenerator(snapshot, repo_model)
            cached_pages = gen.generate_all_pages()
            cache.store_pages(repo_id, analysis_run_id, snapshot.commit_hash, cached_pages)

    return {
        "status": "SUCCESS",
        "analysis_run_id": analysis_run_id,
        "count": len(cached_pages),
        "pages": [p.to_dict() for p in cached_pages],
    }


@router.get("/{analysis_run_id}/pages/{page_id}")
def get_wiki_page_by_id(analysis_run_id: str, page_id: str):
    """Returns a single verified documentation page with claims, citations, and diagrams."""
    from devlensx.api.main import global_state
    registry = get_snapshot_registry()
    snapshot = registry.get(analysis_run_id)

    repo_id = snapshot.repository_id if snapshot else "default"
    commit_hash = snapshot.commit_hash if snapshot else None

    cache = get_documentation_cache()
    page = cache.get_page(repo_id, analysis_run_id, commit_hash, page_id)

    if not page:
        repo_model = global_state.get("repo_model") or {}
        if snapshot:
            gen = DocumentationPageGenerator(snapshot, repo_model)
            pages = gen.generate_all_pages()
            cache.store_pages(repo_id, analysis_run_id, commit_hash, pages)
            page = cache.get_page(repo_id, analysis_run_id, commit_hash, page_id)

    if not page:
        raise HTTPException(status_code=404, detail=f"Documentation page '{page_id}' not found for run '{analysis_run_id}'.")

    return page.to_dict()


@router.post("/{analysis_run_id}/generate")
def trigger_wiki_generation(analysis_run_id: str):
    """Triggers on-demand regeneration of verified documentation pages."""
    from devlensx.api.main import global_state
    registry = get_snapshot_registry()
    snapshot = registry.get(analysis_run_id)
    repo_model = global_state.get("repo_model") or {}

    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Analysis snapshot '{analysis_run_id}' not found in registry.")

    gen = DocumentationPageGenerator(snapshot, repo_model)
    pages = gen.generate_all_pages()
    get_documentation_cache().store_pages(snapshot.repository_id, analysis_run_id, snapshot.commit_hash, pages)

    return {
        "status": "SUCCESS",
        "analysis_run_id": analysis_run_id,
        "generated_pages_count": len(pages),
        "pages": [p.to_dict() for p in pages],
    }
