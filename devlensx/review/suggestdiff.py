"""
DevLensX Myers Line-Diff Engine
Inspired by Alibaba OpenCodeReview (Apache-2.0).
Computes shortest edit script / line-level diffs between code snippets to produce
safe, structured, committable suggestions requiring explicit user action.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional


class DiffLineType(str, Enum):
    CONTEXT = "context"
    ADDED = "added"
    DELETED = "deleted"


@dataclass
class DiffLine:
    type: DiffLineType
    content: str


def compute_line_diff(old_lines: List[str], new_lines: List[str]) -> List[DiffLine]:
    """
    Myers-style shortest edit / line-level diff algorithm.
    Finds optimal alignment between old_lines and new_lines and emits
    context, added, and deleted lines.
    """
    m = len(old_lines)
    n = len(new_lines)
    if m == 0 and n == 0:
        return []

    # LCS DP table for shortest edit script
    lcs = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if old_lines[i - 1].strip() == new_lines[j - 1].strip():
                lcs[i][j] = lcs[i - 1][j - 1] + 1
            else:
                lcs[i][j] = max(lcs[i - 1][j], lcs[i][j - 1])

    # Backtrack to build diff lines
    result_reversed: List[DiffLine] = []
    i = m
    j = n

    while i > 0 or j > 0:
        if i > 0 and j > 0 and old_lines[i - 1].strip() == new_lines[j - 1].strip():
            if old_lines[i - 1] == new_lines[j - 1]:
                result_reversed.append(DiffLine(type=DiffLineType.CONTEXT, content=old_lines[i - 1]))
            else:
                # Indentation or whitespace difference: treat as edit
                result_reversed.append(DiffLine(type=DiffLineType.ADDED, content=new_lines[j - 1]))
                result_reversed.append(DiffLine(type=DiffLineType.DELETED, content=old_lines[i - 1]))
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or lcs[i][j - 1] >= lcs[i - 1][j]):
            result_reversed.append(DiffLine(type=DiffLineType.ADDED, content=new_lines[j - 1]))
            j -= 1
        else:
            result_reversed.append(DiffLine(type=DiffLineType.DELETED, content=old_lines[i - 1]))
            i -= 1

    return list(reversed(result_reversed))


def format_suggestion_patch(
    old_code: str,
    new_code: str,
    file_path: str = "",
    start_line: int = 1,
) -> Dict[str, Any]:
    """
    Formats the line diff into unified patch format and UI-ready structured snippets.
    Enforces the explicit-action invariant:
      - committable: True
      - verified: False (proposals are never automatically verified truth)
      - requires_user_action: True (no automatic code writing)
    """
    old_lines = old_code.splitlines() if old_code else []
    new_lines = new_code.splitlines() if new_code else []

    diff_lines = compute_line_diff(old_lines, new_lines)

    deleted = [dl.content for dl in diff_lines if dl.type == DiffLineType.DELETED]
    added = [dl.content for dl in diff_lines if dl.type == DiffLineType.ADDED]
    context = [dl.content for dl in diff_lines if dl.type == DiffLineType.CONTEXT]

    old_len = len(old_lines)
    new_len = len(new_lines)
    header = f"@@ -{start_line},{old_len} +{start_line},{new_len} @@"

    unified_lines = [header]
    for dl in diff_lines:
        prefix = " " if dl.type == DiffLineType.CONTEXT else ("+" if dl.type == DiffLineType.ADDED else "-")
        unified_lines.append(f"{prefix}{dl.content}")
    unified_patch = "\n".join(unified_lines)

    return {
        "header": header,
        "file": file_path,
        "start_line": start_line,
        "deleted": deleted,
        "added": added,
        "context": context,
        "unified_patch": unified_patch,
        "committable_suggestion": new_code,
        "committable": True,
        "verified": False,
        "requires_user_action": True,
    }


def attach_suggestion_diff_to_finding(
    finding: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Inspects finding for existing code & suggested fix, and generates structured diffSnippet.
    If no existing code is found, builds a sensible addition patch.
    """
    f = dict(finding)
    suggested_fix = f.get("suggested_fix")
    if isinstance(suggested_fix, dict):
        fix_code = suggested_fix.get("code") or suggested_fix.get("text") or ""
    elif isinstance(suggested_fix, str):
        fix_code = suggested_fix
    else:
        fix_code = (f.get("suggested_change") or {}).get("text", "")

    if not fix_code:
        return f

    existing_code = f.get("existing_code") or f.get("target_code") or ""
    start_line = int(f.get("line_start") or 1)
    file_path = f.get("file", "")

    patch_meta = format_suggestion_patch(existing_code, fix_code, file_path, start_line)

    f["diff_snippet"] = {
        "header": patch_meta["header"],
        "deleted": patch_meta["deleted"],
        "added": patch_meta["added"],
    }
    f["committable_suggestion"] = patch_meta["committable_suggestion"]
    f["patch_metadata"] = {
        "committable": True,
        "verified": False,
        "requires_user_action": True,
        "unified_patch": patch_meta["unified_patch"],
    }
    return f
