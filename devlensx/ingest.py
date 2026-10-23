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
from urllib.parse import urlparse, urljoin, urlsplit
import socket
import ipaddress
import select
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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
    submodules: Optional[bool] = False
    compact_tree: Optional[bool] = False


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
    allowed_enterprise = [
        h.strip().lower() for h in os.environ.get("GITHUB_ENTERPRISE_HOSTS", "").split(",") if h.strip()
    ]
    if hostname != "github.com" and hostname not in allowed_enterprise:
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


def resolve_git_relative_url(parent_url: str, rel_url: str) -> str:
    """
    Resolves relative submodule URLs using Git's documented relative-URL semantics.
    Git treats the superproject's repository path like a directory:
    - If rel_url starts with '../': pops the last path segment (whether ending in .git or not).
    - If rel_url starts with './': stays in current repository path (appends inside parent directory).
    - If rel_url does not start with './' or '../': returns clean_rel unchanged, as Git does not resolve it relative to parent.
    """
    clean_rel = rel_url.replace("\\", "/").strip()
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', clean_rel):
        return clean_rel
    if not (clean_rel.startswith("./") or clean_rel.startswith("../")):
        return clean_rel

    parsed = urlparse(parent_url)
    parent_path = parsed.path.rstrip("/")
    segments = [s for s in parent_path.split("/") if s]
    for part in clean_rel.split("/"):
        if part == "..":
            if not segments:
                raise HTTPException(status_code=403, detail=f"Relative submodule URL '{rel_url}' traverses above repository root.")
            segments.pop()
        elif part == "." or part == "":
            continue
        else:
            segments.append(part)
    resolved_path = "/" + "/".join(segments)
    return f"{parsed.scheme}://{parsed.netloc}{resolved_path}"


DISALLOWED_HOST_NAMES = (
    "localhost", "127.0.0.1", "::1", "0.0.0.0",
    "instance-data", "169.254.169.254", "metadata.google.internal"
)


def validate_destination_address(host: str, port: int = 443) -> str:
    """
    Validates host resolution at TCP connect time.
    Guarantees destination restriction, preventing DNS rebinding.
    """
    clean_host = (host or "").lower()
    if clean_host in DISALLOWED_HOST_NAMES:
        raise HTTPException(
            status_code=403,
            detail=f"Host '{host}' is disallowed under network security policy."
        )

    try:
        entries = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise HTTPException(
            status_code=400,
            detail=f"DNS resolution failed for submodule host '{host}': {e}"
        )

    for entry in entries:
        ip_str = entry[4][0]
        ip = ipaddress.ip_address(ip_str)
        is_nat64 = (ip.version == 6 and ip in ipaddress.ip_network("64:ff9b::/96"))

        if is_nat64:
            embedded_ipv4 = ipaddress.IPv4Address(ip.packed[12:])
            if (embedded_ipv4.is_loopback or embedded_ipv4.is_private or embedded_ipv4.is_link_local or
                embedded_ipv4.is_reserved or embedded_ipv4.is_multicast or embedded_ipv4.is_unspecified):
                raise HTTPException(
                    status_code=403,
                    detail=f"Submodule host '{host}' resolves to NAT64 address '{ip}' with disallowed embedded IPv4 '{embedded_ipv4}'."
                )
        elif ip.version == 6 and ip.ipv4_mapped:
            embedded_ipv4 = ip.ipv4_mapped
            if (embedded_ipv4.is_loopback or embedded_ipv4.is_private or embedded_ipv4.is_link_local or
                embedded_ipv4.is_reserved or embedded_ipv4.is_multicast or embedded_ipv4.is_unspecified):
                raise HTTPException(
                    status_code=403,
                    detail=f"Submodule host '{host}' resolves to IPv4-mapped address with disallowed destination: {embedded_ipv4}"
                )
        elif (ip.is_loopback or ip.is_private or ip.is_link_local or
              ip.is_multicast or ip.is_unspecified or ip.is_reserved):
            raise HTTPException(
                status_code=403,
                detail=f"Submodule host '{host}' resolves to private/disallowed IP: {ip_str}"
            )
        return ip_str

    raise HTTPException(
        status_code=403,
        detail=f"No routable addresses found for '{host}'."
    )


class _EgressProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_CONNECT(self):
        # RFC 7230 / RFC 9112 compliant authority parsing with bracketed IPv6 support.
        # Authority-form MUST strictly be uri-host:port without credentials, path, query, or fragment.
        raw_target = self.path.strip()
        try:
            parsed = urlsplit(f"//{raw_target}")
            host = parsed.hostname
            port = parsed.port if parsed.port is not None else 443
        except Exception:
            self.send_error(400, f"Malformed CONNECT destination: {self.path}")
            return

        if (
            not host
            or parsed.username is not None
            or parsed.password is not None
            or bool(parsed.query)
            or bool(parsed.fragment)
            or bool(parsed.path)
        ):
            self.send_error(400, f"Malformed CONNECT destination: {self.path}")
            return

        # P0/P1 Audit Enforcement: Destination port MUST be strictly 443 (HTTPS)
        if port != 443:
            self.send_error(
                403,
                f"Egress security policy violation: destination port {port} is prohibited. Strictly port 443 (HTTPS) is permitted."
            )
            return

        try:
            safe_ip = validate_destination_address(host, port)
        except HTTPException as exc:
            self.send_error(exc.status_code, exc.detail)
            return
        except Exception as err:
            self.send_error(403, f"Egress security policy violation: {err}")
            return

        try:
            # P0 Audit Enforcement: Pin socket directly to safe_ip (IP literal prevents secondary DNS resolution TOCTOU)
            upstream_sock = socket.create_connection((safe_ip, port), timeout=10)
        except Exception as err:
            self.send_error(502, f"Gateway connection error: {err}")
            return

        self.send_response(200, "Connection Established")
        self.end_headers()

        conns = [self.connection, upstream_sock]
        try:
            while True:
                r, _, _ = select.select(conns, [], [], 15)
                if not r:
                    break
                for s in r:
                    other = upstream_sock if s is self.connection else self.connection
                    data = s.recv(16384)
                    if not data:
                        return
                    other.sendall(data)
        finally:
            upstream_sock.close()


class ValidatingEgressProxy:
    def __init__(self):
        self.server = HTTPServer(("127.0.0.1", 0), _EgressProxyHandler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return f"http://127.0.0.1:{self.port}"

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def clone_repository(
    clone_url: str,
    target_dir: Path,
    branch: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = 60,
    submodules: bool = False,
) -> None:
    """
    Clone a repository with single-branch depth 1.
    Never logs or leaks the token.
    Enforces timeout, protocol allowlists, connection-time validating proxy, and bounded depth.
    """
    # Prefer explicit token or fallback to environment
    active_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    final_url = clone_url
    if active_token:
        # Securely inject token for authentication
        parsed = urlparse(clone_url)
        final_url = f"https://x-access-token:{active_token}@{parsed.netloc}{parsed.path}"

    try:
        with ValidatingEgressProxy() as proxy_url:
            # Base clone is always shallow depth 1, single-branch, with protocol and proxy restrictions
            cmd = [
                "git",
                "-c", f"http.proxy={proxy_url}",
                "-c", "protocol.allow=never",
                "-c", "protocol.https.allow=always",
                "-c", "http.followRedirects=false",
                "clone", "--depth", "1", "--single-branch"
            ]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([final_url, str(target_dir)])

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
                
            # P0 Audit Fix: Bounded Submodule Ingestion with Strict Count, Depth, Host & Network Policies
            if submodules:
                gitmodules_path = target_dir / ".gitmodules"
                if gitmodules_path.exists():
                    try:
                        gitmodules_content = gitmodules_path.read_text(encoding="utf-8", errors="replace")
                    except Exception as e:
                        raise HTTPException(status_code=400, detail=f"Cannot read .gitmodules: {str(e)}")

                    submodule_urls = re.findall(r'url\s*=\s*([^\r\n]+)', gitmodules_content)
                    if not submodule_urls and len(gitmodules_content.strip()) > 0 and "[submodule" in gitmodules_content:
                        raise HTTPException(status_code=400, detail="Malformed or unparseable .gitmodules file.")

                    # 1. Submodule Count Limit (Max 5)
                    MAX_SUBMODULES = 5
                    if len(submodule_urls) > MAX_SUBMODULES:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Repository exceeds maximum allowed submodule count ({len(submodule_urls)} > {MAX_SUBMODULES})."
                        )

                    for raw_s_url in submodule_urls:
                        # Git-documented relative URL resolution semantics
                        s_url = resolve_git_relative_url(clone_url, raw_s_url)
                        parsed_s = urlparse(s_url)

                        # Strictly require https protocol; reject file://, ssh://, git://, http://
                        if parsed_s.scheme != "https":
                            raise HTTPException(
                                status_code=403,
                                detail=f"Submodule URL '{raw_s_url}' violates network access policy: strictly HTTPS required (got '{parsed_s.scheme}')."
                            )

                        host = (parsed_s.hostname or "").lower()
                        if not host:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Submodule URL '{raw_s_url}' does not specify a valid hostname."
                            )

                        # Validate destination address immediately as well
                        validate_destination_address(host, 443)

                    # 2. Explicit Depth 1 Bounded Initialization with Proxy, Protocol & Redirect Hardening
                    submodule_cmd = [
                        "git",
                        "-c", f"http.proxy={proxy_url}",
                        "-c", "protocol.allow=never",
                        "-c", "protocol.https.allow=always",
                        "-c", "http.followRedirects=false",
                        "submodule", "update", "--init", "--depth", "1"
                    ]
                    sub_proc = subprocess.run(
                        submodule_cmd,
                        cwd=str(target_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=min(45, timeout),
                    )
                    if sub_proc.returncode != 0:
                        clean_sub_err = mask_token(sub_proc.stderr)
                        raise HTTPException(status_code=400, detail=f"Submodule initialization failed: {clean_sub_err.strip()}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Git clone timed out after {timeout} seconds.")
    except HTTPException:
        raise
    except Exception as e:
        clean_msg = mask_token(str(e))
        raise HTTPException(status_code=500, detail=f"Git clone error: {clean_msg}")


def build_compact_tree(root_name: str, relative_paths: List[str]) -> str:
    """
    Constructs a token-efficient compact directory tree format:
    Collapses single-child hierarchies and groups directory members.
    """
    lines = [f"{root_name}/"]
    grouped: Dict[str, List[str]] = {}
    for p in sorted(relative_paths):
        parent = str(Path(p).parent).replace("\\", "/")
        if parent == ".":
            parent = ""
        grouped.setdefault(parent, []).append(Path(p).name)

    for folder, files in sorted(grouped.items()):
        prefix = f"  {folder}/" if folder else "  "
        if len(files) <= 6:
            lines.append(f"{prefix}{{{', '.join(files)}}}")
        else:
            lines.append(f"{prefix}({len(files)} files: {', '.join(files[:4])}, ...)")
    return "\n".join(lines)


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
    compact_tree: bool = False,
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

    if compact_tree:
        tree_str = build_compact_tree(walk_root.name, rel_path_list)
    else:
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
    submodules: bool = False,
    compact_tree: bool = False,
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
    filter_sig = f"{include_patterns}:{exclude_patterns}:{file_size_cap}:{branch}:{parsed.subpath}:{submodules}:{compact_tree}"
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
            compact_tree=compact_tree,
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
                submodules=submodules,
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
                compact_tree=compact_tree,
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
            # Guarantee resilient cleanup of clone temporary directory across Windows read-only git locks
            try:
                temp_dir_obj.cleanup()
            except Exception:
                def _handle_readonly(func, path, exc):
                    import stat
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass
                if temp_path.exists():
                    shutil.rmtree(temp_path, onerror=_handle_readonly)

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
    submodules: bool = False,
    compact_tree: bool = False,
) -> IngestResult:
    """
    Streaming-friendly async wrapper that delegates to a threadpool.
    Does not block the FastAPI event loop during clone and filesystem traversal.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _THREAD_POOL,
        lambda: ingest_repository_sync(
            url_or_path=url_or_path,
            branch=branch,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_file_size=max_file_size,
            token=token,
            full=full,
            persist_cloned_dir=persist_cloned_dir,
            submodules=submodules,
            compact_tree=compact_tree,
        ),
    )


def get_cached_ingest(ingest_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached ingest entry by ingest ID."""
    entry = _INGEST_CACHE.get(ingest_id)
    if entry and (time.time() - entry["cached_at"] < CACHE_TTL_SECONDS):
        return entry
    return None
