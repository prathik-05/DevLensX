"""
DevLensX Native GitIngest Engine.
Converts Git repositories or local directories into structured, unified text digests
optimized for Large Language Models (LLMs) with summary, directory tree, and file contents.
"""

from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import pathspec
from fastapi import HTTPException
from pydantic import BaseModel, Field

from devlensx.repository import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_EXTENSIONS,
    DEFAULT_EXCLUDE_FILENAMES,
    is_safe_symlink,
    is_vendored_or_nested_git,
    should_skip_dir,
    should_skip_file,
)

_THREAD_POOL = ThreadPoolExecutor(max_workers=4)

# Rate limiting storage: IP -> list of timestamps
_RATE_LIMIT_STORE: Dict[str, List[float]] = {}
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60.0

# Ingest cache storage: cache_key -> { "result": IngestResult, "cached_at": float, "cloned_path": Optional[str] }
_INGEST_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600.0  # 1 hour

LANGUAGE_MAP: Dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".java": "Java",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".rs": "Rust",
    ".go": "Go",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".c": "C",
    ".h": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".scala": "Scala",
    ".dart": "Dart",
    ".r": "R",
    ".lua": "Lua",
}


class IngestFile(BaseModel):
    path: str
    size: int
    language: str
    content: Optional[str] = None
    tokens: int


class IngestSummary(BaseModel):
    repo_name: str
    branch: str
    commit_sha: str
    file_count: int
    total_bytes: int
    estimated_tokens: int


class IngestResult(BaseModel):
    id: str
    summary: IngestSummary
    tree: str
    files: List[IngestFile]
    digest: str


class IngestRequest(BaseModel):
    url: str
    branch: Optional[str] = None
    include_patterns: Optional[Union[str, List[str]]] = None
    exclude_patterns: Optional[Union[str, List[str]]] = None
    max_file_size: Optional[int] = 1024 * 1024  # 1 MB default
    token: Optional[str] = None


@dataclass
class ParsedSource:
    is_local: bool
    local_path: Optional[Path] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    branch: Optional[str] = None
    subpath: Optional[str] = None
    clone_url: Optional[str] = None
    repo_name: str = ""


def check_rate_limit(client_ip: str) -> None:
    """Enforce rate limits per IP address."""
    now = time.time()
    timestamps = _RATE_LIMIT_STORE.get(client_ip, [])
    # Filter out entries older than window
    valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(valid_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait before submitting more ingest requests.")
    valid_timestamps.append(now)
    _RATE_LIMIT_STORE[client_ip] = valid_timestamps


def parse_github_url(url_or_path: str) -> ParsedSource:
    """
    Parse a GitHub URL or local path.
    Enforces SSRF protection: only github.com is permitted for URLs.
    Detects branch, subpath, .git suffix, and guards against path traversal.
    """
    clean = url_or_path.strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Repository URL or path cannot be empty.")

    # Check for local directory path
    is_local_candidate = (
        clean.startswith("/")
        or clean.startswith("\\")
        or bool(re.match(r"^[a-zA-Z]:", clean))
        or clean.startswith("./")
        or clean.startswith(".\\")
        or clean.startswith("../")
        or clean.startswith("..\\")
        or os.path.isabs(clean)
        or (not clean.startswith("http://") and not clean.startswith("https://") and os.path.isdir(clean))
    )

    if is_local_candidate:
        p = Path(clean)
        try:
            resolved = p.resolve()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid local path provided.")
        if not resolved.exists() or not resolved.is_dir():
            raise HTTPException(status_code=400, detail=f"Local repository path does not exist or is not a directory: {clean}")
        return ParsedSource(is_local=True, local_path=resolved, repo_name=resolved.name)

    # Normalize github.com URL without scheme
    if clean.startswith("github.com/"):
        clean = "https://" + clean

    # URL validation & SSRF protection
    parsed = urlparse(clean)
    if not parsed.scheme or not parsed.netloc:
        # Check if user provided owner/repo shorthand e.g. "owner/repo"
        parts = clean.split("/")
        if len(parts) == 2 and not any(c in clean for c in [":", "\\", " "]):
            owner, repo = parts
            clean = f"https://github.com/{owner}/{repo}"
            parsed = urlparse(clean)
        else:
            raise HTTPException(status_code=400, detail="Invalid URL or path format. Expected github.com URL or local directory.")

    hostname = (parsed.hostname or "").lower()
    if hostname != "github.com":
        raise HTTPException(
            status_code=400,
            detail=f"SSRF Protection: Host '{hostname}' is not permitted. Only 'github.com' is allowed.",
        )

    # Path parsing: /owner/repo[/tree/branch[/subpath]]
    segments = [seg for seg in parsed.path.strip("/").split("/") if seg]
    if len(segments) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL. Expected format: https://github.com/{owner}/{repo}")

    owner = segments[0]
    repo = segments[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    branch: Optional[str] = None
    subpath: Optional[str] = None

    if len(segments) >= 4 and segments[2] == "tree":
        branch = segments[3]
        if len(segments) > 4:
            subpath_parts = segments[4:]
            if any(part in {"..", "."} for part in subpath_parts):
                raise HTTPException(status_code=400, detail="Path traversal attempt in subpath is forbidden.")
            subpath = "/".join(subpath_parts)

    clone_url = f"https://github.com/{owner}/{repo}.git"
    return ParsedSource(
        is_local=False,
        owner=owner,
        repo=repo,
        branch=branch,
        subpath=subpath,
        clone_url=clone_url,
        repo_name=repo,
    )


def is_binary(file_path: Path) -> bool:
    """Check if file is binary by sniffing for null bytes in the first 8KB."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except Exception:
        return True


def detect_language(file_path: Path) -> str:
    """Detect programming or markup language from file extension."""
    ext = file_path.suffix.lower()
    return LANGUAGE_MAP.get(ext, "Text")


def estimate_tokens(text: str) -> int:
    """Estimate token count with tiktoken (cl100k_base) and fallback to len/4."""
    if not text:
        return 0
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text, disallowed_special=()))
    except Exception:
        return max(1, len(text) // 4)


def mask_token(text: str) -> str:
    """Mask credentials and tokens in command outputs or URLs."""
    return re.sub(r"://[^@\s]+@", "://***@", text)


def clone_repository(
    clone_url: str,
    target_dir: Path,
    branch: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = 60,
) -> None:
    """
    Clone a repository with single-branch depth 1.
    Never logs or leaks the token.
    Enforces timeout.
    """
    # Prefer explicit token or fallback to environment
    active_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    final_url = clone_url
    if active_token:
        # Securely inject token for authentication
        parsed = urlparse(clone_url)
        final_url = f"https://x-access-token:{active_token}@{parsed.netloc}{parsed.path}"

    cmd = ["git", "clone", "--depth", "1", "--single-branch"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([final_url, str(target_dir)])

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            clean_err = mask_token(proc.stderr)
            raise HTTPException(status_code=400, detail=f"Git clone failed: {clean_err.strip()}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Git clone timed out after {timeout} seconds.")
    except HTTPException:
        raise
    except Exception as e:
        clean_msg = mask_token(str(e))
        raise HTTPException(status_code=500, detail=f"Git clone error: {clean_msg}")


def build_ascii_tree(root_name: str, relative_paths: List[str]) -> str:
    """
    Construct an ASCII tree representation of the ingested files.
    """
    tree: Dict[str, Any] = {}
    for p in sorted(relative_paths):
        parts = Path(p).parts
        curr = tree
        for part in parts:
            if part not in curr:
                curr[part] = {}
            curr = curr[part]

    lines = [f"{root_name}/"]

    def _render(node: Dict[str, Any], prefix: str = "") -> None:
        keys = sorted(node.keys())
        for idx, key in enumerate(keys):
            is_last = idx == (len(keys) - 1)
            connector = "└── " if is_last else "├── "
            child_prefix = "    " if is_last else "│   "
            lines.append(f"{prefix}{connector}{key}")
            _render(node[key], prefix + child_prefix)

    _render(tree)
    return "\n".join(lines)


def _collect_files(
    repo_root: Path,
    subpath: Optional[str] = None,
    include_patterns: Optional[Union[str, List[str]]] = None,
    exclude_patterns: Optional[Union[str, List[str]]] = None,
    max_file_size: int = 1024 * 1024,
    total_cap: int = 50 * 1024 * 1024,
) -> Tuple[List[IngestFile], str, int]:
    """
    Walk directory, filter according to rules, and collect file contents.
    Enforces per-file cap and total digest cap.
    """
    walk_root = (repo_root / subpath) if subpath else repo_root
    if not walk_root.exists() or not walk_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Subpath '{subpath}' not found in repository.")

    # Load root .gitignore if present
    gitignore_spec: Optional[pathspec.PathSpec] = None
    gitignore_file = repo_root / ".gitignore"
    if gitignore_file.exists() and gitignore_file.is_file():
        try:
            with open(gitignore_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if lines:
                    gitignore_spec = pathspec.PathSpec.from_lines("gitignore", lines)
        except Exception:
            gitignore_spec = None

    # Parse user include patterns
    inc_spec: Optional[pathspec.PathSpec] = None
    if include_patterns:
        if isinstance(include_patterns, str):
            pats = [p.strip() for p in include_patterns.split(",") if p.strip()]
        else:
            pats = [p.strip() for p in include_patterns if p.strip()]
        if pats:
            inc_spec = pathspec.PathSpec.from_lines("gitignore", pats)

    # Parse user exclude patterns
    exc_spec: Optional[pathspec.PathSpec] = None
    if exclude_patterns:
        if isinstance(exclude_patterns, str):
            pats = [p.strip() for p in exclude_patterns.split(",") if p.strip()]
        else:
            pats = [p.strip() for p in exclude_patterns if p.strip()]
        if pats:
            exc_spec = pathspec.PathSpec.from_lines("gitignore", pats)

    ingest_files: List[IngestFile] = []
    rel_path_list: List[str] = []
    total_bytes = 0

    for root, dirs, files in os.walk(walk_root, followlinks=False):
        current_dir = Path(root)

        # Prevent following symlinks outside root
        if not is_safe_symlink(current_dir, repo_root):
            dirs.clear()
            continue

        # Filter directories in-place
        dirs[:] = [
            d for d in dirs
            if not should_skip_dir(d, current_dir / d, repo_root)
        ]

        for fname in sorted(files):
            file_path = current_dir / fname

            # Skip based on repository rules
            if should_skip_file(fname, file_path, repo_root):
                continue

            rel_from_repo = file_path.resolve().relative_to(repo_root.resolve()).as_posix()

            # Check .gitignore
            if gitignore_spec and gitignore_spec.match_file(rel_from_repo):
                continue

            # Check user exclude patterns
            if exc_spec and exc_spec.match_file(rel_from_repo):
                continue

            # Check user include patterns
            if inc_spec and not inc_spec.match_file(rel_from_repo):
                continue

            # Check binary
            if is_binary(file_path):
                continue

            try:
                stat = file_path.stat()
                file_size = stat.st_size
            except Exception:
                continue

            # Per-file cap
            if file_size > max_file_size:
                continue

            # Check total digest cap
            if total_bytes + file_size > total_cap:
                break

            # Read content
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content_str = f.read()
            except Exception:
                continue

            tokens = estimate_tokens(content_str)
            lang = detect_language(file_path)

            ingest_files.append(
                IngestFile(
                    path=rel_from_repo,
                    size=file_size,
                    language=lang,
                    content=content_str,
                    tokens=tokens,
                )
            )
            rel_path_list.append(rel_from_repo)
            total_bytes += file_size

    tree_str = build_ascii_tree(walk_root.name, rel_path_list)
    return ingest_files, tree_str, total_bytes


def _format_digest(tree: str, files: List[IngestFile]) -> str:
    """Format full digest string matching gitingest standard."""
    chunks = [
        "Directory structure:",
        tree,
        "",
    ]
    for file_item in files:
        chunks.append("================================================")
        chunks.append(f"FILE: {file_item.path}")
        chunks.append("================================================")
        chunks.append(file_item.content or "")
        chunks.append("")
    return "\n".join(chunks)


def _get_git_commit_sha(repo_dir: Path) -> str:
    """Get HEAD commit SHA or fallback to clean hash."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return "0000000000000000000000000000000000000000"


def _get_git_branch(repo_dir: Path, requested_branch: Optional[str] = None) -> str:
    """Get active branch name."""
    if requested_branch:
        return requested_branch
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "main"


def ingest_repository_sync(
    url_or_path: str,
    branch: Optional[str] = None,
    include_patterns: Optional[Union[str, List[str]]] = None,
    exclude_patterns: Optional[Union[str, List[str]]] = None,
    max_file_size: Optional[int] = 1024 * 1024,
    token: Optional[str] = None,
    full: bool = False,
    persist_cloned_dir: bool = True,
) -> IngestResult:
    """
    Synchronous core ingest worker function.
    Clones or uses local repo in a TemporaryDirectory, filters files,
    builds ASCII tree, calculates tokens, and formats LLM prompt digest.
    Always cleans up temporary resources unless persistent cache requested.
    """
    parsed = parse_github_url(url_or_path)
    file_size_cap = max_file_size or (1024 * 1024)

    # Compute cache key from input parameters
    filter_sig = f"{include_patterns}:{exclude_patterns}:{file_size_cap}:{branch}:{parsed.subpath}"
    filter_hash = hashlib.sha256(filter_sig.encode()).hexdigest()[:12]

    # Persistent holding directory for /api/analyze/from-ingest
    cached_cloned_dir: Optional[str] = None

    if parsed.is_local:
        repo_dir = parsed.local_path
        commit_sha = _get_git_commit_sha(repo_dir)
        active_branch = _get_git_branch(repo_dir, branch)
        repo_name = parsed.repo_name

        cache_key = f"{repo_dir.resolve()}:{commit_sha}:{filter_hash}"
        cached_entry = _INGEST_CACHE.get(cache_key)
        if cached_entry and (time.time() - cached_entry["cached_at"] < CACHE_TTL_SECONDS):
            res: IngestResult = cached_entry["result"]
            if not full:
                res_copy = res.model_copy(deep=True)
                for f in res_copy.files:
                    f.content = None
                return res_copy
            return res

        files, tree_str, total_bytes = _collect_files(
            repo_root=repo_dir,
            subpath=parsed.subpath,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_file_size=file_size_cap,
        )
    else:
        # Clone into a temporary directory
        temp_dir_obj = tempfile.TemporaryDirectory()
        try:
            temp_path = Path(temp_dir_obj.name)
            clone_repository(
                clone_url=parsed.clone_url,
                target_dir=temp_path,
                branch=branch or parsed.branch,
                token=token,
                timeout=60,
            )

            commit_sha = _get_git_commit_sha(temp_path)
            active_branch = _get_git_branch(temp_path, branch or parsed.branch)
            repo_name = parsed.repo_name

            cache_key = f"{parsed.owner}/{parsed.repo}:{commit_sha}:{filter_hash}"
            cached_entry = _INGEST_CACHE.get(cache_key)
            if cached_entry and (time.time() - cached_entry["cached_at"] < CACHE_TTL_SECONDS):
                res: IngestResult = cached_entry["result"]
                if not full:
                    res_copy = res.model_copy(deep=True)
                    for f in res_copy.files:
                        f.content = None
                    return res_copy
                return res

            files, tree_str, total_bytes = _collect_files(
                repo_root=temp_path,
                subpath=parsed.subpath,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                max_file_size=file_size_cap,
            )

            if persist_cloned_dir:
                # Retain cloned directory in a managed cache location for /api/analyze/from-ingest
                cache_hold = Path(tempfile.gettempdir()) / "devlensx_ingest_cache" / f"{parsed.repo}_{commit_sha[:8]}"
                if cache_hold.exists():
                    shutil.rmtree(cache_hold, ignore_errors=True)
                cache_hold.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(temp_path, cache_hold)
                cached_cloned_dir = str(cache_hold)

        finally:
            # Guarantee cleanup of clone temporary directory
            temp_dir_obj.cleanup()

    full_digest = _format_digest(tree_str, files)
    total_tokens = estimate_tokens(full_digest)

    summary = IngestSummary(
        repo_name=repo_name,
        branch=active_branch,
        commit_sha=commit_sha,
        file_count=len(files),
        total_bytes=total_bytes,
        estimated_tokens=total_tokens,
    )

    ingest_id = hashlib.sha256(f"{repo_name}_{commit_sha}_{time.time()}".encode()).hexdigest()[:16]

    result = IngestResult(
        id=ingest_id,
        summary=summary,
        tree=tree_str,
        files=files,
        digest=full_digest,
    )

    # Store in memory cache
    _INGEST_CACHE[cache_key] = {
        "result": result,
        "cached_at": time.time(),
        "cloned_path": cached_cloned_dir or (str(parsed.local_path) if parsed.is_local else None),
        "id": ingest_id,
    }
    # Also index by ingest_id for fast lookup
    _INGEST_CACHE[ingest_id] = _INGEST_CACHE[cache_key]

    if not full:
        # Strip file contents from returned model if full=False
        result_copy = result.model_copy(deep=True)
        for f in result_copy.files:
            f.content = None
        return result_copy

    return result


async def ingest_repository(
    url_or_path: str,
    branch: Optional[str] = None,
    include_patterns: Optional[Union[str, List[str]]] = None,
    exclude_patterns: Optional[Union[str, List[str]]] = None,
    max_file_size: Optional[int] = 1024 * 1024,
    token: Optional[str] = None,
    full: bool = False,
    persist_cloned_dir: bool = True,
) -> IngestResult:
    """
    Streaming-friendly async wrapper that delegates to a threadpool.
    Does not block the FastAPI event loop during clone and filesystem traversal.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _THREAD_POOL,
        ingest_repository_sync,
        url_or_path,
        branch,
        include_patterns,
        exclude_patterns,
        max_file_size,
        token,
        full,
        persist_cloned_dir,
    )


def get_cached_ingest(ingest_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached ingest entry by ingest ID."""
    entry = _INGEST_CACHE.get(ingest_id)
    if entry and (time.time() - entry["cached_at"] < CACHE_TTL_SECONDS):
        return entry
    return None
