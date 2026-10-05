"""Smart File Grouping & Token Budgeting Engine.

Ported and extended from Alibaba's OpenCodeReview (internal/agent/grouping.go).
Handles large multi-file pull requests by calculating diff churn, estimating token consumption,
and partitioning diffs into semantic, budget-respecting subtasks. Prevents LLM context blowout.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

MAX_FILES_PER_GROUP = 10
DEFAULT_SMALL_CHANGE_MAX_FILES = 5
DEFAULT_SMALL_CHANGE_MAX_CHURN = 300
DEFAULT_GROUP_TOKEN_BUDGET = 6000
FIXED_PROMPT_TOKEN_OVERHEAD = 350
TOKENS_PER_DIFF_LINE = 1.35


@dataclass
class FileDiffMeta:
    path: str
    diff_text: str
    added: int = 0
    deleted: int = 0
    churn: int = 0
    estimated_tokens: int = 0


@dataclass
class FileGroup:
    label: str
    files: List[FileDiffMeta] = field(default_factory=list)
    total_churn: int = 0
    estimated_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "file_count": len(self.files),
            "files": [f.path for f in self.files],
            "total_churn": self.total_churn,
            "estimated_tokens": self.estimated_tokens,
        }


def calculate_diff_churn(diff_text: str) -> Tuple[int, int, int]:
    """Calculate (added, deleted, total_churn) for a single file diff."""
    added = 0
    deleted = 0
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            deleted += 1
    return added, deleted, added + deleted


def estimate_diff_tokens(diff_text: str) -> int:
    """Estimate token count for a diff text, including header overhead."""
    lines = diff_text.splitlines()
    line_tokens = int(len(lines) * TOKENS_PER_DIFF_LINE)
    return FIXED_PROMPT_TOKEN_OVERHEAD + line_tokens


def parse_diff_files(raw_diff: str) -> List[FileDiffMeta]:
    """Parse a unified git diff into individual file chunks."""
    files: List[FileDiffMeta] = []
    current_path: Optional[str] = None
    current_lines: List[str] = []

    def commit_current():
        if current_path and current_lines:
            text = "\n".join(current_lines)
            added, deleted, churn = calculate_diff_churn(text)
            tok = estimate_diff_tokens(text)
            files.append(
                FileDiffMeta(
                    path=current_path,
                    diff_text=text,
                    added=added,
                    deleted=deleted,
                    churn=churn,
                    estimated_tokens=tok,
                )
            )

    for line in raw_diff.splitlines():
        if line.startswith("diff --git "):
            commit_current()
            parts = line.split(" ")
            # Take b/path or a/path
            if len(parts) >= 4:
                b_path = parts[3]
                current_path = b_path[2:] if b_path.startswith("b/") else b_path
            else:
                current_path = "unknown"
            current_lines = [line]
        elif current_path is not None:
            current_lines.append(line)
        else:
            # If no diff header yet, match +++ b/...
            if line.startswith("+++ b/"):
                current_path = line[6:]
                current_lines = [line]

    commit_current()

    # Fallback if no git diff header matched (e.g. raw single hunk)
    if not files and raw_diff.strip():
        added, deleted, churn = calculate_diff_churn(raw_diff)
        tok = estimate_diff_tokens(raw_diff)
        files.append(
            FileDiffMeta(
                path="patch.diff",
                diff_text=raw_diff,
                added=added,
                deleted=deleted,
                churn=churn,
                estimated_tokens=tok,
            )
        )

    return files


def group_diffs(
    diff_files: List[FileDiffMeta],
    max_files_per_group: int = MAX_FILES_PER_GROUP,
    token_budget: int = DEFAULT_GROUP_TOKEN_BUDGET,
    small_change_max_files: int = DEFAULT_SMALL_CHANGE_MAX_FILES,
    small_change_max_churn: int = DEFAULT_SMALL_CHANGE_MAX_CHURN,
) -> List[FileGroup]:
    """Group file diffs into manageable batches for LLM review.

    Strategy:
    1. Single file: 1 group.
    2. Small change set: bundle all together as "small change set" if within token budget.
    3. Large PR: group by directory prefix / component, respecting max files & token budget.
    """
    if not diff_files:
        return []

    if len(diff_files) == 1:
        f = diff_files[0]
        return [
            FileGroup(
                label=f.path,
                files=[f],
                total_churn=f.churn,
                estimated_tokens=f.estimated_tokens,
            )
        ]

    total_churn = sum(f.churn for f in diff_files)
    total_tokens = sum(f.estimated_tokens for f in diff_files)

    # Check if this qualifies as a small change set
    if (
        len(diff_files) <= small_change_max_files
        and total_churn <= small_change_max_churn
        and total_tokens <= token_budget
    ):
        return [
            FileGroup(
                label="small change set",
                files=diff_files,
                total_churn=total_churn,
                estimated_tokens=total_tokens,
            )
        ]

    # Group by directory prefix (semantic grouping)
    dir_buckets: Dict[str, List[FileDiffMeta]] = {}
    for f in diff_files:
        parent_dir = os.path.dirname(f.path) or "root"
        # Extract top-level module (e.g. backend/ or frontend/)
        top_module = parent_dir.split(os.sep)[0].split("/")[0]
        dir_buckets.setdefault(top_module, []).append(f)

    raw_groups: List[FileGroup] = []
    for module_name, files_in_module in dir_buckets.items():
        # Sub-partition files within module to respect max_files and token_budget
        cur_group_files: List[FileDiffMeta] = []
        cur_churn = 0
        cur_tokens = 0

        for f in files_in_module:
            if (
                len(cur_group_files) >= max_files_per_group
                or (cur_tokens + f.estimated_tokens) > token_budget
            ) and cur_group_files:
                raw_groups.append(
                    FileGroup(
                        label=f"{module_name} (part {len(raw_groups) + 1})",
                        files=cur_group_files,
                        total_churn=cur_churn,
                        estimated_tokens=cur_tokens,
                    )
                )
                cur_group_files = [f]
                cur_churn = f.churn
                cur_tokens = f.estimated_tokens
            else:
                cur_group_files.append(f)
                cur_churn += f.churn
                cur_tokens += f.estimated_tokens

        if cur_group_files:
            lbl = (
                module_name
                if not raw_groups or not raw_groups[-1].label.startswith(module_name)
                else f"{module_name} (part {len(raw_groups) + 1})"
            )
            raw_groups.append(
                FileGroup(
                    label=lbl,
                    files=cur_group_files,
                    total_churn=cur_churn,
                    estimated_tokens=cur_tokens,
                )
            )

    return raw_groups
