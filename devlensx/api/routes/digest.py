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


def _run_ingest(
    source: str,
    max_file_size: int = 10 * 1024 * 1024,
    include_patterns: Optional[str] = None,
    exclude_patterns: Optional[str] = None,
    branch: Optional[str] = None,
    tag: Optional[str] = None,
    token: Optional[str] = None,
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
        summary_text = (
            f"Repository: {res.summary.repo_name}\n"
            f"Files analyzed: {res.summary.file_count}\n"
            f"Commit: {res.summary.commit_sha[:10]}\n"
            f"Branch: {res.summary.branch}\n"
        )
        content_chunks = []
        for f in res.files:
            content_chunks.append("================================================")
            content_chunks.append(f"FILE: {f.path}")
            content_chunks.append("================================================")
            content_chunks.append(f.content or "")
            content_chunks.append("")
        files_content = "\n".join(content_chunks)

        prompt_digest = (
            f"# CODEBASE DIGEST & ARCHITECTURE CONTEXT\n\n"
            f"{summary_text}\n\n"
            f"## Directory Structure\n```\n{res.tree}\n```\n\n"
            f"## Codebase Files\n{files_content}\n"
        )

        return {
            "success": True,
            "source": source,
            "summary": summary_text,
            "tree": res.tree,
            "content": files_content,
            "prompt_digest": prompt_digest,
            "stats": {
                "files_analyzed": res.summary.file_count,
                "total_size_bytes": res.summary.total_bytes,
                "total_size_formatted": _format_size(res.summary.total_bytes),
                "estimated_tokens": res.summary.estimated_tokens,
                "estimated_tokens_formatted": f"{res.summary.estimated_tokens / 1000:.1f}k" if res.summary.estimated_tokens >= 1000 else str(res.summary.estimated_tokens),
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
    """
    source = (req.source or "").strip()
    if not source or source == "current":
        # Resolve active repository from global_state
        try:
            from devlensx.api.main import global_state
            brain = global_state.get("brain")
            repo_model = global_state.get("repo_model") or {}
            source = (brain.repo_path if brain else None) or repo_model.get("repo_path") or os.getcwd()
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
    )


@router.get("/current")
def get_current_repo_digest():
    """
    Convenience endpoint: Generates digest for the currently loaded repository in DevLensX.
    """
    try:
        from devlensx.api.main import global_state
        brain = global_state.get("brain")
        repo_model = global_state.get("repo_model") or {}
        source = (brain.repo_path if brain else None) or repo_model.get("repo_path") or os.getcwd()
    except Exception:
        source = os.getcwd()

    return _run_ingest(source=source)
