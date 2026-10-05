"""P1-B hunk-level unified diff parser.

Pure string processing — never touches the filesystem, so malicious paths
(traversal, null bytes, absolute paths) are inert by construction. They are
parsed as opaque labels and flagged, never resolved or opened.

Produces FileDiff records preserving: path, old_path, status, hunks with
old/new line ranges plus added/removed line numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from devlensx.core.config import (
    MAX_REVIEW_FILES,
    MAX_REVIEW_HUNKS_PER_FILE,
    MAX_REVIEW_TOTAL_HUNKS,
)

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DIFF_GIT_RE = re.compile(r"^diff --git\s+(\S+)\s+(\S+)\s*$")


def _strip_git_prefix(p: str) -> str:
    if p.startswith("a/") or p.startswith("b/"):
        return p[2:]
    return p


def _clean_path(p: str) -> str:
    """Remove null bytes/control chars for safe downstream display. Kept opaque."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", p).strip().strip('"')[:512]


@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added: List[int] = field(default_factory=list)      # new-file line numbers
    removed: List[int] = field(default_factory=list)    # old-file line numbers

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "added": self.added,
            "removed": self.removed,
        }


@dataclass
class FileDiff:
    path: str                      # new path (or old path for deletions)
    old_path: Optional[str] = None
    status: str = "MODIFIED"       # ADDED | MODIFIED | DELETED | RENAMED | COPIED | BINARY | TYPECHANGE
    hunks: List[Hunk] = field(default_factory=list)
    binary: bool = False
    suspicious_path: bool = False  # traversal / absolute / null-byte input observed

    @property
    def added_lines(self) -> List[int]:
        out: List[int] = []
        for h in self.hunks:
            out.extend(h.added)
        return out

    @property
    def removed_lines(self) -> List[int]:
        out: List[int] = []
        for h in self.hunks:
            out.extend(h.removed)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "old_path": self.old_path,
            "status": self.status,
            "binary": self.binary,
            "suspicious_path": self.suspicious_path,
            "hunks": [h.to_dict() for h in self.hunks],
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
        }


@dataclass
class ParseResult:
    files: List[FileDiff] = field(default_factory=list)
    truncated: bool = False
    truncated_reason: str = ""
    diagnostics: List[str] = field(default_factory=list)


def _looks_suspicious(p: str) -> bool:
    return (
        ".." in p.replace("\\", "/").split("/")
        or p.startswith("/")
        or "\x00" in p
        or bool(re.match(r"^[A-Za-z]:", p))
    )


class HunkParser:
    """Parse unified diffs into FileDiff records."""

    @staticmethod
    def parse(
        diff: str,
        max_files: int = MAX_REVIEW_FILES,
        max_hunks_per_file: int = MAX_REVIEW_HUNKS_PER_FILE,
        max_total_hunks: int = MAX_REVIEW_TOTAL_HUNKS,
    ) -> ParseResult:
        result = ParseResult()
        if not diff or not diff.strip():
            return result

        current: Optional[FileDiff] = None
        old_side: Optional[str] = None   # from --- line
        new_side: Optional[str] = None   # from +++ line
        hunk: Optional[Hunk] = None
        old_ln = new_ln = 0
        total_hunks = 0
        pending_rename_from: Optional[str] = None

        def flush_file() -> None:
            nonlocal current, hunk, old_side, new_side
            if current is not None:
                # Resolve status from ---/+++ markers when headers were absent
                if current.status == "MODIFIED":
                    if old_side in ("/dev/null", "dev/null"):
                        current.status = "ADDED"
                        if not current.old_path:
                            current.old_path = None
                    elif new_side in ("/dev/null", "dev/null"):
                        current.status = "DELETED"
                result.files.append(current)
            current = None
            hunk = None
            old_side = None
            new_side = None

        for raw in diff.splitlines():
            line = raw.rstrip("\n")
            if not line:
                continue

            m = _DIFF_GIT_RE.match(line)
            if m:
                flush_file()
                if len(result.files) >= max_files:
                    result.truncated = True
                    result.truncated_reason = f"file limit ({max_files}) exceeded"
                    result.diagnostics.append(result.truncated_reason)
                    break
                a_raw, b_raw = _clean_path(m.group(1)), _clean_path(m.group(2))
                current = FileDiff(path=_strip_git_prefix(b_raw))
                if _looks_suspicious(a_raw) or _looks_suspicious(b_raw):
                    current.suspicious_path = True
                    result.diagnostics.append(f"suspicious path quarantined as label: {b_raw[:120]}")
                pending_rename_from = None
                continue

            if current is None:
                # Lines outside any file block (e.g. bare +++ without diff --git)
                if line.startswith("+++ ") or line.startswith("--- "):
                    flush_file()  # no-op safeguard
                continue

            if line.startswith("old mode") or line.startswith("new mode"):
                continue
            if line.startswith("new file mode"):
                current.status = "ADDED"
                continue
            if line.startswith("deleted file mode"):
                current.status = "DELETED"
                continue
            if line.startswith("similarity index"):
                continue
            if line.startswith("dissimilarity index"):
                continue
            if line.startswith("rename from "):
                pending_rename_from = _clean_path(line[len("rename from "):])
                continue
            if line.startswith("rename to "):
                new_name = _clean_path(line[len("rename to "):])
                current.status = "RENAMED"
                current.old_path = pending_rename_from or current.old_path
                current.path = _strip_git_prefix(new_name)
                if _looks_suspicious(new_name):
                    current.suspicious_path = True
                pending_rename_from = None
                continue
            if line.startswith("copy from ") or line.startswith("copy to "):
                current.status = "COPIED"
                continue
            if line.startswith("Binary files ") and "differ" in line:
                current.binary = True
                current.status = "BINARY"
                continue
            if line.startswith("--- "):
                old_side = _clean_path(line[4:].split("\t")[0])
                if old_side in ("/dev/null", "dev/null") and current.status == "MODIFIED":
                    current.status = "ADDED"
                continue
            if line.startswith("+++ "):
                new_side = _clean_path(line[4:].split("\t")[0])
                if new_side in ("/dev/null", "dev/null"):
                    current.status = "DELETED"
                    # For deletions the usable path is the old side
                    if old_side and old_side not in ("/dev/null", "dev/null"):
                        current.path = _strip_git_prefix(old_side)
                elif new_side not in ("", "/dev/null", "dev/null"):
                    # Trust +++ side for the display path when no git header existed
                    current.path = _strip_git_prefix(new_side)
                continue

            hm = _HUNK_RE.match(line)
            if hm:
                if total_hunks >= max_total_hunks:
                    result.truncated = True
                    result.truncated_reason = f"hunk limit ({max_total_hunks}) exceeded"
                    result.diagnostics.append(result.truncated_reason)
                    hunk = None
                    continue
                if len(current.hunks) >= max_hunks_per_file:
                    if not result.truncated:
                        result.truncated = True
                        result.truncated_reason = f"per-file hunk limit ({max_hunks_per_file}) exceeded"
                        result.diagnostics.append(result.truncated_reason)
                    hunk = None
                    continue
                old_ln = int(hm.group(1))
                new_ln = int(hm.group(3))
                hunk = Hunk(
                    old_start=old_ln,
                    old_count=int(hm.group(2)) if hm.group(2) is not None else 1,
                    new_start=new_ln,
                    new_count=int(hm.group(4)) if hm.group(4) is not None else 1,
                )
                current.hunks.append(hunk)
                total_hunks += 1
                continue

            if hunk is None:
                # Context outside hunks (e.g. index lines, "No newline" markers)
                continue
            if line.startswith("\\ "):
                continue
            if line.startswith("+") and not line.startswith("+++"):
                hunk.added.append(new_ln)
                new_ln += 1
            elif line.startswith("-") and not line.startswith("---"):
                hunk.removed.append(old_ln)
                old_ln += 1
            else:
                # Context line (leading space or anything else): advance both
                old_ln += 1
                new_ln += 1

        flush_file()
        return result
