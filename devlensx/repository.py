"""
DevLensX Repository Scanning & Path Filtering Utilities.
Contains vendored-directory, nested git repo, and artifact skipping logic.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Set, Union

DEFAULT_EXCLUDE_DIRS: Set[str] = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".gradle",
    "bin",
    "obj",
    "vendor",
    "third_party",
    ".next",
    ".turbo",
    ".idea",
    ".vscode",
    ".gitattributes",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
}

DEFAULT_EXCLUDE_EXTENSIONS: Set[str] = {
    # Lockfiles
    ".lock",
    # Minified & Source Maps
    ".map",
    # Images & Media
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".webp",
    ".bmp",
    ".tiff",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".mp3",
    ".wav",
    # Fonts
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    # Archives & Packages
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".jar",
    ".war",
    # Binaries & Compiled
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".iso",
    ".o",
    ".a",
    ".pyc",
    ".pyd",
    ".class",
    ".wasm",
}

DEFAULT_EXCLUDE_FILENAMES: Set[str] = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
    "pipfile.lock",
    "composer.lock",
    "bun.lockb",
}


def is_safe_symlink(path: Union[str, Path], root: Union[str, Path]) -> bool:
    """
    Ensure symlinks do not escape the repo root (prevent path traversal).
    """
    try:
        resolved_path = Path(path).resolve()
        resolved_root = Path(root).resolve()
        return resolved_root in resolved_path.parents or resolved_path == resolved_root
    except Exception:
        return False


def is_vendored_or_nested_git(path: Union[str, Path], root: Union[str, Path]) -> bool:
    """
    Determine if a path represents a vendored directory, external dependency,
    or nested git repository.
    """
    p = Path(path)
    root_p = Path(root).resolve()
    try:
        rel = p.resolve().relative_to(root_p)
    except ValueError:
        return True  # Escapes root

    parts = set(rel.parts)
    if parts.intersection(DEFAULT_EXCLUDE_DIRS):
        return True

    # Nested git check
    if p.is_dir() and (p / ".git").exists() and p.resolve() != root_p:
        return True

    return False


def should_skip_dir(dir_name: str, dir_path: Path, root: Path) -> bool:
    """
    Check if a directory should be skipped during walk.
    """
    if dir_name in DEFAULT_EXCLUDE_DIRS or dir_name.startswith("."):
        if dir_name not in {".", "./"}:
            return True
    if not is_safe_symlink(dir_path, root):
        return True
    return is_vendored_or_nested_git(dir_path, root)


def should_skip_file(file_name: str, file_path: Path, root: Path) -> bool:
    """
    Check if a file should be skipped (lockfiles, minified files, binaries, images).
    """
    lower_name = file_name.lower()
    if lower_name in DEFAULT_EXCLUDE_FILENAMES:
        return True

    ext = file_path.suffix.lower()
    if ext in DEFAULT_EXCLUDE_EXTENSIONS:
        return True

    if lower_name.endswith(".min.js") or lower_name.endswith(".min.css") or lower_name.endswith(".bundle.js"):
        return True

    if not is_safe_symlink(file_path, root):
        return True

    return False
