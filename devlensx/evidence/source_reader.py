"""
DevLensX Evidence Source Reader (D5)

Reads source lines from a repository snapshot with strict safety controls.
Repository code is UNTRUSTED INPUT:
  - paths are validated against the snapshot root (no traversal, no symlinks out)
  - file size is bounded
  - binary content is detected and refused
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple

from devlensx.evidence.models import (
    ResolutionStatus,
    ResolvedEvidence,
    EvidenceRef,
    SourceLine,
)

MAX_FILE_BYTES = 1_000_000        # 1 MB per source file
MAX_CONTEXT_LINES = 400           # max lines returned around a range
BINARY_SNIFF_BYTES = 1024


class SourceReader:
    """Safety-bounded reader for files inside a registered snapshot."""

    def __init__(self, repo_path: str):
        self.repo_root = Path(repo_path).resolve()

    # ------------------------------------------------------------------
    def _safe_target(self, rel_path: str) -> Optional[Path]:
        """Resolves a repo-relative path, refusing any escape from the root."""
        if not rel_path or not rel_path.strip() or "\x00" in rel_path:
            return None
        # Block absolute paths (Unix-style) BEFORE normalization
        if rel_path.startswith("/"):
            return None
        # Block Windows absolute paths
        if len(rel_path) >= 2 and rel_path[1] == ":":
            return None
        normalized = rel_path.replace("\\", "/").lstrip("/")
        # Block Windows absolute paths (drive letter after normalization)
        if len(normalized) >= 2 and normalized[1] == ":":
            return None
        # Block traversal
        if any(part in ("..",) for part in normalized.split("/")):
            return None
        target = (self.repo_root / normalized).resolve()
        try:
            target.relative_to(self.repo_root)
        except ValueError:
            return None
        return target

    # ------------------------------------------------------------------
    @staticmethod
    def _looks_binary(path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                chunk = f.read(BINARY_SNIFF_BYTES)
        except OSError:
            return True
        if b"\x00" in chunk:
            return True
        if not chunk:
            return False
        text_chars = bytes(range(32, 127)) + b"\n\r\t\f\b"
        nontext = sum(1 for b in chunk if b not in text_chars)
        return nontext / max(len(chunk), 1) > 0.30

    # ------------------------------------------------------------------
    def read_range(
        self,
        ref: EvidenceRef,
        context_lines: int = 5,
    ) -> ResolvedEvidence:
        """Reads the cited line range plus surrounding context.

        Returns RESOLVED with lines on success; otherwise an honest
        non-resolved status. Never raises for expected failure modes.
        """
        line_start = max(1, int(ref.line_start or 1))
        line_end = max(line_start, int(ref.line_end or line_start))
        # Invalid if end < start (after normalization)
        if int(ref.line_end or line_start) < int(ref.line_start or 1):
            return ResolvedEvidence(
                status=ResolutionStatus.INVALID_RANGE,
                ref=ref,
                message="Line end is before line start.",
            )
        if line_end - line_start + 1 > MAX_CONTEXT_LINES * 2:
            return ResolvedEvidence(
                status=ResolutionStatus.INVALID_RANGE,
                ref=ref,
                message=f"Requested range {line_start}-{line_end} exceeds maximum window.",
            )

        target = self._safe_target(ref.file_path)
        if target is None:
            return ResolvedEvidence(
                status=ResolutionStatus.PATH_VIOLATION,
                ref=ref,
                message="Citation path escapes the repository snapshot root.",
            )

        if not target.is_file():
            return ResolvedEvidence(
                status=ResolutionStatus.FILE_NOT_FOUND,
                ref=ref,
                message=f"File '{ref.file_path}' does not exist in this snapshot.",
            )

        if target.is_symlink():
            resolved_link = target.resolve()
            try:
                resolved_link.relative_to(self.repo_root)
            except ValueError:
                return ResolvedEvidence(
                    status=ResolutionStatus.PATH_VIOLATION,
                    ref=ref,
                    message="File is a symlink escaping the repository root.",
                )

        try:
            size = os.path.getsize(target)
            if size > MAX_FILE_BYTES:
                return ResolvedEvidence(
                    status=ResolutionStatus.FILE_TOO_LARGE,
                    ref=ref,
                    message=f"File exceeds {MAX_FILE_BYTES} byte limit ({size} bytes).",
                )
        except OSError as exc:
            return ResolvedEvidence(
                status=ResolutionStatus.FILE_NOT_FOUND,
                ref=ref,
                message=f"Cannot stat file: {exc}",
            )

        if self._looks_binary(target):
            return ResolvedEvidence(
                status=ResolutionStatus.BINARY_FILE,
                ref=ref,
                message="Refusing to display binary content.",
            )

        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ResolvedEvidence(
                status=ResolutionStatus.FILE_NOT_FOUND,
                ref=ref,
                message=f"Cannot read file: {exc}",
            )

        all_lines = text.splitlines()
        total = len(all_lines)

        ctx_start = max(1, line_start - context_lines)
        ctx_end = min(total, line_end + context_lines)

        lines: List[SourceLine] = []
        for n in range(ctx_start, ctx_end + 1):
            lines.append(SourceLine(
                line_number=n,
                content=all_lines[n - 1],
                in_range=line_start <= n <= line_end,
            ))

        return ResolvedEvidence(
            status=ResolutionStatus.RESOLVED,
            ref=ref,
            message="OK",
            lines=lines,
            total_lines=total,
        )