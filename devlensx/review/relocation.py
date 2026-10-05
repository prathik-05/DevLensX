"""
DevLensX Diff Relocation & Line Resolver
Inspired by Alibaba OpenCodeReview (Apache-2.0).
Resolves LLM line drift via diff hunk matching and unique cross-file relocation.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class IndexedLine:
    line_num: int
    content: str


@dataclass
class HunkLine:
    type: str  # " " (context), "+" (added), "-" (deleted)
    content: str


@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[HunkLine] = field(default_factory=list)


@dataclass
class DiffFile:
    old_path: str
    new_path: str
    hunks: List[DiffHunk] = field(default_factory=list)
    raw_diff: str = ""


def parse_diff_files(diff_text: str) -> List[DiffFile]:
    """Parse unified git diff into DiffFile objects with structured hunks."""
    files: List[DiffFile] = []
    lines = diff_text.splitlines()
    i = 0
    n = len(lines)

    current_file: Optional[DiffFile] = None

    while i < n:
        line = lines[i]

        if line.startswith("diff --git"):
            if current_file:
                files.append(current_file)
            parts = line.split()
            old_p = parts[2][2:] if len(parts) > 2 and parts[2].startswith("a/") else ""
            new_p = parts[3][2:] if len(parts) > 3 and parts[3].startswith("b/") else ""
            current_file = DiffFile(old_path=old_p, new_path=new_p, raw_diff=line + "\n")
            i += 1
            continue

        if current_file:
            current_file.raw_diff += line + "\n"

            if line.startswith("--- a/"):
                current_file.old_path = line[6:].strip()
            elif line.startswith("+++ b/"):
                current_file.new_path = line[6:].strip()
            elif line.startswith("@@"):
                # Hunk header @@ -old_start,old_count +new_start,new_count @@
                m = re.search(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                if m:
                    old_start = int(m.group(1))
                    old_count = int(m.group(2) or 1)
                    new_start = int(m.group(3))
                    new_count = int(m.group(4) or 1)
                    hunk = DiffHunk(
                        old_start=old_start,
                        old_count=old_count,
                        new_start=new_start,
                        new_count=new_count,
                    )
                    current_file.hunks.append(hunk)

            elif current_file.hunks and len(line) > 0:
                prefix = line[0]
                content = line[1:]
                if prefix in (" ", "+", "-"):
                    current_file.hunks[-1].lines.append(HunkLine(type=prefix, content=content))

        i += 1

    if current_file:
        files.append(current_file)

    return files


def normalize_line(s: str) -> str:
    """Normalize code line by stripping surrounding whitespace."""
    return s.strip()


def split_and_normalize(code_snippet: str) -> List[str]:
    """Split snippet into non-empty normalized lines."""
    res: List[str] = []
    for line in code_snippet.splitlines():
        n = normalize_line(line)
        if n:
            res.append(n)
    return res


def extract_side_lines(hunk: DiffHunk, new_side: bool) -> List[IndexedLine]:
    """
    Extract side lines from hunk.
    new_side=True  -> context + added lines with new-file line numbers.
    new_side=False -> context + deleted lines with old-file line numbers.
    """
    res: List[IndexedLine] = []
    old_line = hunk.old_start
    new_line = hunk.new_start

    for l in hunk.lines:
        if l.type == " ":
            line_num = new_line if new_side else old_line
            res.append(IndexedLine(line_num=line_num, content=normalize_line(l.content)))
            old_line += 1
            new_line += 1
        elif l.type == "+":
            if new_side:
                res.append(IndexedLine(line_num=new_line, content=normalize_line(l.content)))
            new_line += 1
        elif l.type == "-":
            if not new_side:
                res.append(IndexedLine(line_num=old_line, content=normalize_line(l.content)))
            old_line += 1

    return res


def match_consecutive(
    side_lines: List[IndexedLine], target_lines: List[str]
) -> Tuple[Optional[int], Optional[int], bool]:
    """Match consecutive run of target_lines inside side_lines."""
    if not target_lines or len(side_lines) < len(target_lines):
        return None, None, False

    # Filter out blank side lines for matching, but retain original line numbers
    valid_side = [l for l in side_lines if l.content]
    if len(valid_side) < len(target_lines):
        return None, None, False

    for i in range(len(valid_side) - len(target_lines) + 1):
        matched = True
        for j, target in enumerate(target_lines):
            if valid_side[i + j].content != target:
                matched = False
                break
        if matched:
            start_line = valid_side[i].line_num
            end_line = valid_side[i + len(target_lines) - 1].line_num
            return start_line, end_line, True

    return None, None, False


def resolve_from_hunks(diff_file: DiffFile, existing_code: str) -> Optional[Tuple[int, int]]:
    """Try matching existing_code in the diff file's hunks (new side first, then old side)."""
    target = split_and_normalize(existing_code)
    if not target or not diff_file.hunks:
        return None

    # Try new side first (added/context lines)
    for hunk in diff_file.hunks:
        new_side = extract_side_lines(hunk, new_side=True)
        start, end, ok = match_consecutive(new_side, target)
        if ok and start is not None and end is not None:
            return start, end

    # Fallback: old side (deleted/context lines)
    for hunk in diff_file.hunks:
        old_side = extract_side_lines(hunk, new_side=False)
        start, end, ok = match_consecutive(old_side, target)
        if ok and start is not None and end is not None:
            return start, end

    return None


def relocate_across_files(
    reported_file: str,
    existing_code: str,
    diff_files: List[DiffFile],
) -> Tuple[Optional[str], Optional[Tuple[int, int]], bool]:
    """
    Search other changed files in the diff for a UNIQUE match of existing_code.
    Returns:
        (new_path, (start, end), is_ambiguous)
        - Unique match: (path, (start, end), False)
        - Ambiguous (>1 matches): (None, None, True)
        - No match (0 matches): (None, None, False)
    """
    hits: List[Tuple[str, Tuple[int, int]]] = []

    for df in diff_files:
        p = df.new_path or df.old_path
        if p == reported_file or not p:
            continue
        res = resolve_from_hunks(df, existing_code)
        if res:
            hits.append((p, res))
            if len(hits) > 1:
                # Ambiguous: multiple files match identical code -> cannot guess
                return None, None, True

    if len(hits) == 1:
        hit_path, span = hits[0]
        return hit_path, span, False

    return None, None, False


def relocate_and_resolve_findings(
    findings: List[Dict[str, Any]],
    diff_text: str,
) -> List[Dict[str, Any]]:
    """
    Primary entry point:
    Resolves line numbers and relocates findings across files when misattributed.
    Enforces the user invariant:
      - Unique match -> relocate with accurate EvidenceRef line range
      - Ambiguous match -> INSUFFICIENT_EVIDENCE (never guess!)
    """
    diff_files = parse_diff_files(diff_text)
    file_map: Dict[str, DiffFile] = {}
    for df in diff_files:
        if df.new_path:
            file_map[df.new_path] = df
            file_map[df.new_path.replace("\\", "/")] = df
        if df.old_path:
            file_map[df.old_path] = df
            file_map[df.old_path.replace("\\", "/")] = df

    out: List[Dict[str, Any]] = []

    for raw in findings:
        f = dict(raw)
        f_file = (f.get("file") or "").replace("\\", "/")
        existing_code = f.get("existing_code") or f.get("target_code") or ""

        if not existing_code:
            # Nothing to relocate or match against
            out.append(f)
            continue

        # Try matching in the reported file first
        target_df = file_map.get(f_file)
        if not target_df:
            # Check basename or partial path
            for path_key, df in file_map.items():
                if path_key.endswith(f_file) or f_file.endswith(path_key):
                    target_df = df
                    break

        resolved = False
        if target_df:
            span = resolve_from_hunks(target_df, existing_code)
            if span:
                f["line_start"] = span[0]
                f["line_end"] = span[1]
                f["resolved_by"] = "hunk_match"
                resolved = True

        if not resolved:
            # Cross-file relocation attempt
            relocated_file, span, is_ambiguous = relocate_across_files(f_file, existing_code, diff_files)

            if is_ambiguous:
                # User constraint: Ambiguous match across multiple files -> INSUFFICIENT_EVIDENCE
                f["verdict"] = "INSUFFICIENT_EVIDENCE"
                f["status"] = "INSUFFICIENT_EVIDENCE"
                f["evidence_refs"] = []
                f["rationale"] = (
                    f"Ambiguous snippet match: '{existing_code[:40]}...' matches multiple "
                    f"files in the diff. Cannot establish unique location."
                )
                f["line_start"] = 0
                f["line_end"] = 0
            elif relocated_file and span:
                # Unique match found in another diff file
                f["original_file"] = f_file
                f["file"] = relocated_file
                f["line_start"] = span[0]
                f["line_end"] = span[1]
                f["relocated_from"] = f_file
                f["resolved_by"] = "cross_file_relocation"

        out.append(f)

    return out
