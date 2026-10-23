"""
DevLensX GitIngest Code Context & Prompt Digest API Routes
Integrates GitIngest to convert Git repositories or local directories into structured,
unified text digests optimized for Large Language Models (LLMs).
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/wiki/digest", tags=["Code Context Digest (GitIngest)"])


class DigestRequest(BaseModel):
    source: Optional[str] = None
    analysis_run_id: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10 MB default
    include_patterns: Optional[str] = None
    exclude_patterns: Optional[str] = None
    branch: Optional[str] = None
    tag: Optional[str] = None
    token: Optional[str] = None


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def _estimate_tokens(text: str) -> int:
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text, disallowed_special=()))
    except Exception:
        # Fallback heuristic: ~4 characters per token
        return max(1, len(text) // 4)


def _extract_manifest_and_stack_evidence(
    files_list,
    repo_model: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None
) -> Dict[str, Any]:
    from devlensx.understanding.profiling.repository_profiler import RepositoryProfiler

    classes = (repo_model.get("classes") or []) if repo_model else []
    resolved_path = source or (repo_model.get("repo_path") if repo_model else "") or ""
    profile = RepositoryProfiler.profile_repository(
        repo_path=resolved_path,
        classes=classes,
        repo_model=repo_model,
        files=files_list,
    )

    manifest_names = {
        "package.json": "Node.js / npm",
        "pom.xml": "Java / Maven",
        "build.gradle": "Java / Gradle",
        "build.gradle.kts": "Kotlin / Gradle",
        "requirements.txt": "Python / pip",
        "pyproject.toml": "Python / pyproject",
        "setup.py": "Python / setuptools",
        "Cargo.toml": "Rust / Cargo",
        "go.mod": "Go / Modules",
        "Dockerfile": "Docker Container",
        "docker-compose.yml": "Docker Compose",
    }
    manifests = []

    # Extract manifests from actual files list (handles nested and monorepo manifests)
    file_paths = []
    for f in files_list:
        if isinstance(f, dict):
            file_paths.append(f.get("path", ""))
        elif hasattr(f, "path"):
            file_paths.append(str(getattr(f, "path", "")))
        else:
            file_paths.append(str(f))

    for fp in file_paths:
        base = os.path.basename(fp)
        if base in manifest_names:
            manifests.append(f"{fp} ({manifest_names[base]})")
        elif fp.endswith(".csproj") or fp.endswith(".sln"):
            manifests.append(f"{fp} (.NET / C#)")

    # Supplement with disk-inspected manifests from profile
    for m in profile.get("manifests_found", []):
        desc = manifest_names.get(m, "Build / Package Manifest")
        if not any(m in existing for existing in manifests):
            manifests.append(f"{m} ({desc})")

    # Entrypoints
    entrypoints = []
    for ep in profile.get("entry_points", []):
        if ep.get("symbol"):
            entrypoints.append(f"`{ep['symbol']}` ({ep.get('file', '')}) &mdash; {ep.get('type', 'Entrypoint')}")
        elif ep.get("file"):
            entrypoints.append(f"`{ep['file']}` ({ep.get('type', 'Application Entrypoint')})")

    # Key symbols: production symbols ranked by architectural priority with explainable tags
    key_symbols = []
    prod_symbols = profile.get("production_symbols", [])
    for s in prod_symbols[:15]:
        nm = s["name"]
        fl = s["file"]
        l1 = s["line_start"]
        l2 = s["line_end"]
        role = s["role"].replace("_", " ").title()
        reason = s["ranking_reason"]
        key_symbols.append(f"- `{nm}` [{role}] in `{fl}#L{l1}-L{l2}` &mdash; {reason}")

    # Test symbols: cleanly segregated into supporting verification evidence
    test_symbols = []
    for t in profile.get("test_symbols", [])[:10]:
        nm = t["name"]
        fl = t["file"]
        l1 = t["line_start"]
        l2 = t["line_end"]
        test_symbols.append(f"- `{nm}` [Test Fixture] in `{fl}#L{l1}-L{l2}`")

    # Data flow derived adaptively from archetype and actual AST relationships
    data_flow = profile.get("data_flow", [])

    return {
        "manifests": manifests,
        "entrypoints": entrypoints,
        "key_symbols": key_symbols,
        "test_symbols": test_symbols,
        "data_flow": data_flow,
        "archetype": profile.get("archetype", "MODULAR_APPLICATION"),
        "archetype_rationale": profile.get("archetype_rationale", ""),
        "primary_language": profile.get("primary_language", "Polyglot"),
        "framework": profile.get("framework", "Standard"),
        "profile": profile,
    }


def _run_ingest(
    source: str,
    max_file_size: int = 10 * 1024 * 1024,
    include_patterns: Optional[str] = None,
    exclude_patterns: Optional[str] = None,
    branch: Optional[str] = None,
    tag: Optional[str] = None,
    token: Optional[str] = None,
    analysis_run_id: Optional[str] = None,
    repo_model: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from devlensx.ingest import ingest_repository_sync

    try:
        res = ingest_repository_sync(
            url_or_path=source,
            branch=branch or tag,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_file_size=max_file_size,
            token=token,
            full=True,
        )

        evidence = _extract_manifest_and_stack_evidence(res.files, repo_model=repo_model, source=source)

        summary_text = (
            f"Repository: {res.summary.repo_name}\n"
            f"Files analyzed: {res.summary.file_count}\n"
            f"Commit: {res.summary.commit_sha[:10]}\n"
            f"Branch: {res.summary.branch}\n"
            f"Archetype: {evidence.get('archetype', 'MODULAR_APPLICATION')}\n"
        )
        content_chunks = []
        for f in res.files:
            content_chunks.append("================================================")
            content_chunks.append(f"FILE: {f.path}")
            content_chunks.append("================================================")
            content_chunks.append(f.content or "")
            content_chunks.append("")
        files_content = "\n".join(content_chunks)

        manifest_section = "\n".join(f"- {m}" for m in evidence["manifests"]) if evidence["manifests"] else "- None detected"
        entry_section = "\n".join(f"- {e}" for e in evidence["entrypoints"]) if evidence["entrypoints"] else "- None detected"
        symbols_section = "\n".join(evidence["key_symbols"]) if evidence["key_symbols"] else "- Insufficient source analysis data — no class structure was extracted"
        flow_section = "\n".join(f"- {df}" for df in evidence["data_flow"]) if evidence["data_flow"] else "- Direct modular execution"
        test_section = "\n".join(evidence["test_symbols"]) if evidence.get("test_symbols") else "- No test fixtures identified in parsed source"

        prompt_digest = (
            f"# CODEBASE DIGEST & ARCHITECTURE CONTEXT\n\n"
            f"> NOTE FOR AI: Focus on production entry points, domain logic, and core algorithms. "
            f"Do not describe test classes or test methods as the primary application components.\n\n"
            f"## 1. Executive Overview\n"
            f"- **Repository:** {res.summary.repo_name}\n"
            f"- **Commit:** {res.summary.commit_sha[:10]} | **Branch:** {res.summary.branch}\n"
            f"- **Primary Stack:** {evidence.get('primary_language', 'Polyglot')} ({evidence.get('framework', 'Standard')})\n"
            f"- **Architectural Archetype:** {evidence.get('archetype', 'MODULAR_APPLICATION')} &mdash; {evidence.get('archetype_rationale', '')}\n"
            f"- **Files Analyzed:** {res.summary.file_count} | **Total Size:** {_format_size(res.summary.total_bytes)} | **Estimated Tokens:** {res.summary.estimated_tokens}\n\n"
            f"## 2. Detected Manifests & Tech Stack\n"
            f"{manifest_section}\n\n"
            f"## 3. Key Entry Points & Grounded Symbols\n"
            f"**Entry Points:**\n{entry_section}\n\n"
            f"**Core Production Symbols & Source Lines:**\n{symbols_section}\n\n"
            f"## 4. Verified Data Flow & Architecture\n"
            f"{flow_section}\n\n"
            f"## 5. Test & Verification Suite\n"
            f"{test_section}\n\n"
            f"## 6. Directory Structure\n```\n{res.tree}\n```\n\n"
            f"## 7. Codebase Files\n{files_content}\n"
        )

        return {
            "success": True,
            "source": source,
            "analysis_run_id": analysis_run_id,
            "summary": summary_text,
            "tree": res.tree,
            "content": files_content,
            "prompt_digest": prompt_digest,
            "manifests": evidence["manifests"],
            "entrypoints": evidence["entrypoints"],
            "key_symbols": evidence["key_symbols"],
            "test_symbols": evidence.get("test_symbols", []),
            "archetype": evidence.get("archetype", "MODULAR_APPLICATION"),
            "primary_language": evidence.get("primary_language", "Polyglot"),
            "stats": {
                "files_analyzed": res.summary.file_count,
                "total_size_bytes": res.summary.total_bytes,
                "total_size_formatted": _format_size(res.summary.total_bytes),
                "estimated_tokens": res.summary.estimated_tokens,
                "estimated_tokens_formatted": f"{res.summary.estimated_tokens / 1000:.1f}k" if res.summary.estimated_tokens >= 1000 else str(res.summary.estimated_tokens),
                "manifests_detected": len(evidence["manifests"]),
                "entrypoints_detected": len(evidence["entrypoints"]),
                "production_symbols_detected": len(evidence["key_symbols"]),
                "test_symbols_detected": len(evidence.get("test_symbols", [])),
            },
        }
    except Exception as native_err:
        # Fallback to gitingest if installed, otherwise re-raise
        try:
            from gitingest import ingest
            inc_set = set(p.strip() for p in include_patterns.split(",") if p.strip()) if include_patterns else None
            exc_set = set(p.strip() for p in exclude_patterns.split(",") if p.strip()) if exclude_patterns else None
            summary, tree, content = ingest(
                source=source,
                max_file_size=max_file_size,
                include_patterns=inc_set,
                exclude_patterns=exc_set,
                branch=branch,
                tag=tag,
                token=token,
            )
            file_count = 0
            token_count = _estimate_tokens(tree + "\n" + content)
            total_bytes = len(content.encode("utf-8", errors="replace"))
            prompt_digest = (
                f"# CODEBASE DIGEST & ARCHITECTURE CONTEXT\n\n"
                f"{summary}\n\n"
                f"## Directory Structure\n```\n{tree}\n```\n\n"
                f"## Codebase Files\n{content}\n"
            )
            return {
                "success": True,
                "source": source,
                "summary": summary,
                "tree": tree,
                "content": content,
                "prompt_digest": prompt_digest,
                "stats": {
                    "files_analyzed": file_count,
                    "total_size_bytes": total_bytes,
                    "total_size_formatted": _format_size(total_bytes),
                    "estimated_tokens": token_count,
                    "estimated_tokens_formatted": f"{token_count / 1000:.1f}k" if token_count >= 1000 else str(token_count),
                },
            }
        except Exception:
            raise HTTPException(status_code=400, detail=f"GitIngest extraction failed: {str(native_err)}")



@router.post("")
def create_digest(req: DigestRequest):
    """
    Converts a Git repository URL or local directory into a unified, structured LLM prompt digest.
    Binds directly to active snapshot or analysis_run_id if provided.
    """
    source = (req.source or "").strip()
    analysis_run_id = req.analysis_run_id
    repo_model = None

    if analysis_run_id:
        try:
            from devlensx.evidence.resolver import get_snapshot_registry
            snap = get_snapshot_registry().get(analysis_run_id)
            if snap:
                source = source or snap.repo_path
                from devlensx.chat.orchestrator import _model_store
                repo_model = _model_store.get(analysis_run_id)
        except Exception:
            pass

    if not source or source == "current":
        # Resolve active repository from global_state
        try:
            from devlensx.api.main import global_state
            brain = global_state.get("brain")
            repo_model = repo_model or global_state.get("repo_model") or {}
            source = (brain.repo_path if brain else None) or repo_model.get("repo_path") or os.getcwd()
            analysis_run_id = analysis_run_id or (getattr(brain, "analysis_run_id", None) if brain else None)
        except Exception:
            source = os.getcwd()

    if not os.path.exists(source) and not (source.startswith("http://") or source.startswith("https://") or "github.com" in source):
        raise HTTPException(status_code=404, detail=f"Source path or repository not found: '{source}'")

    return _run_ingest(
        source=source,
        max_file_size=req.max_file_size,
        include_patterns=req.include_patterns,
        exclude_patterns=req.exclude_patterns,
        branch=req.branch,
        tag=req.tag,
        token=req.token,
        analysis_run_id=analysis_run_id,
        repo_model=repo_model,
    )


@router.get("/current")
def get_current_repo_digest():
    """
    Convenience endpoint: Generates digest for the currently loaded repository in DevLensX.
    """
    analysis_run_id = None
    repo_model = None
    try:
        from devlensx.api.main import global_state
        brain = global_state.get("brain")
        repo_model = global_state.get("repo_model") or {}
        source = (brain.repo_path if brain else None) or repo_model.get("repo_path") or os.getcwd()
        analysis_run_id = getattr(brain, "analysis_run_id", None) if brain else None
    except Exception:
        source = os.getcwd()

    return _run_ingest(source=source, analysis_run_id=analysis_run_id, repo_model=repo_model)


@router.get("/{analysis_run_id}")
def get_snapshot_digest(analysis_run_id: str):
    """
    Generates evidence-grounded prompt digest bound directly to an immutable analysis snapshot.
    """
    from devlensx.evidence.resolver import get_snapshot_registry
    snap = get_snapshot_registry().get(analysis_run_id)
    if not snap:
        raise HTTPException(status_code=404, detail=f"Snapshot '{analysis_run_id}' not found.")

    repo_model = None
    try:
        from devlensx.chat.orchestrator import _model_store
        repo_model = _model_store.get(analysis_run_id)
    except Exception:
        pass
    if not repo_model:
        try:
            from devlensx.core.persistence import get_storage_manager
            recovered = get_storage_manager().load_snapshot(analysis_run_id)
            if recovered:
                repo_model = recovered[1]
        except Exception:
            pass

    return _run_ingest(
        source=snap.repo_path,
        analysis_run_id=analysis_run_id,
        repo_model=repo_model,
    )
