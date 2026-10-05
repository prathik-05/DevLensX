"""P1-B line-to-symbol resolution: changed diff lines -> URM/AST symbols.

A symbol counts as changed IFF at least one added/removed line falls inside
its [line_start, line_end] range in the matching file. Name mentions in
comments, strings, or documentation NEVER qualify — this closes the
substring false-positive in the old file-level matcher.

New-file symbols resolve with change=ADDED (declaration evidence);
deleted-file symbols resolve with change=REMOVED (declaration evidence).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from devlensx.core.config import MAX_REVIEW_SYMBOLS
from devlensx.review.hunks import FileDiff, ParseResult


def _norm(p: str) -> str:
    return (p or "").replace("\\", "/").lstrip("./")


def _same_file(model_file: str, diff_path: str) -> bool:
    mf, dp = _norm(model_file), _norm(diff_path)
    if not mf or not dp:
        return False
    return mf == dp or mf.endswith("/" + dp) or dp.endswith("/" + mf)


@dataclass
class ChangedSymbol:
    name: str
    file: str
    change: str  # ADDED_LINES | REMOVED_LINES | MODIFIED | ADDED_FILE | REMOVED_FILE
    changed_lines: List[int] = field(default_factory=list)   # new-file numbering
    removed_lines: List[int] = field(default_factory=list)   # old-file numbering
    enclosing: str = ""          # innermost scope name when different (method of class)
    evidence_kind: str = "changed-line"  # changed-line | declaration
    is_test: bool = False
    stereotype: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "file": self.file,
            "change": self.change,
            "changed_lines": self.changed_lines,
            "removed_lines": self.removed_lines,
            "enclosing": self.enclosing,
            "evidence_kind": self.evidence_kind,
            "is_test": self.is_test,
            "stereotype": self.stereotype,
        }


def _ranges_overlap(lines: List[int], start: int, end: int) -> List[int]:
    if not start or not end or end < start:
        return []
    return [n for n in lines if start <= n <= end]


def resolve_changed_symbols(
    parsed: ParseResult,
    model: Dict[str, Any],
    max_symbols: int = MAX_REVIEW_SYMBOLS,
) -> List[ChangedSymbol]:
    """Resolve hunk line ranges to model symbols by range containment."""
    classes = [c for c in (model or {}).get("classes", []) if isinstance(c, dict)]
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for c in classes:
        f = _norm(c.get("file") or "")
        if f:
            by_file.setdefault(f, []).append(c)

    out: List[ChangedSymbol] = []
    seen = set()

    def emit(sym: ChangedSymbol) -> None:
        key = (sym.name, sym.file)
        if key in seen or len(out) >= max_symbols:
            return
        seen.add(key)
        out.append(sym)

    for fd in parsed.files:
        if fd.binary:
            continue
        # Candidate model symbols in this file
        cands = [c for key, syms in by_file.items()
                 if _same_file(key, fd.path) or (fd.old_path and _same_file(key, fd.old_path))
                 for c in syms]
        if not cands:
            continue

        if fd.status == "ADDED":
            for c in sorted(cands, key=lambda x: (x.get("line_start") or 0)):
                emit(ChangedSymbol(
                    name=c.get("name", ""), file=c.get("file", ""),
                    change="ADDED_FILE", evidence_kind="declaration",
                    is_test=bool(c.get("is_test")), stereotype=c.get("stereotype", ""),
                ))
            continue
        if fd.status == "DELETED":
            for c in sorted(cands, key=lambda x: (x.get("line_start") or 0)):
                emit(ChangedSymbol(
                    name=c.get("name", ""), file=c.get("file", ""),
                    change="REMOVED_FILE", evidence_kind="declaration",
                    is_test=bool(c.get("is_test")), stereotype=c.get("stereotype", ""),
                ))
            continue

        added, removed = fd.added_lines, fd.removed_lines
        if not added and not removed:
            continue
        for c in cands:
            start, end = c.get("line_start") or 0, c.get("line_end") or 0
            if not start or not end or end < start:
                # Symbol carries no range info (legacy/sparse model): fall back
                # to file-level attribution, explicitly marked as declaration
                # evidence — never as changed-line evidence.
                emit(ChangedSymbol(
                    name=c.get("name", ""), file=c.get("file", ""),
                    change="MODIFIED", evidence_kind="declaration",
                    is_test=bool(c.get("is_test")), stereotype=c.get("stereotype", ""),
                ))
                continue
            hit_added = _ranges_overlap(added, start, end)
            hit_removed = _ranges_overlap(removed, start, end)
            if not hit_added and not hit_removed:
                continue
            kind = c.get("kind", "")
            change = "MODIFIED"
            if hit_added and not hit_removed:
                change = "ADDED_LINES"
            elif hit_removed and not hit_added:
                change = "REMOVED_LINES"
            emit(ChangedSymbol(
                name=c.get("name", ""), file=c.get("file", ""),
                change=change, changed_lines=sorted(hit_added),
                removed_lines=sorted(hit_removed),
                enclosing="", evidence_kind="changed-line",
                is_test=bool(c.get("is_test")), stereotype=c.get("stereotype", ""),
            ))

    # Innermost scope wins: drop class-level entries fully covered by a
    # method-level entry in the same file (keeps findings precise).
    return _prefer_innermost(out, classes)


def _prefer_innermost(syms: List[ChangedSymbol], classes: List[Dict[str, Any]]) -> List[ChangedSymbol]:
    method_like = {"method", "constructor", "function"}
    ranges = {(c.get("name"), _norm(c.get("file") or "")): (c.get("line_start") or 0, c.get("line_end") or 0, c.get("kind", ""))
              for c in classes}
    method_syms = [s for s in syms
                   if ranges.get((s.name, _norm(s.file)), (0, 0, ""))[2] in method_like]
    if not method_syms:
        return syms
    method_ranges = [( _norm(s.file), set(s.changed_lines) | set(s.removed_lines)) for s in method_syms]
    kept: List[ChangedSymbol] = []
    for s in syms:
        kind = ranges.get((s.name, _norm(s.file)), (0, 0, ""))[2]
        if kind in method_like or kind in ("class", "interface"):
            if kind in ("class", "interface"):
                covered = set(s.changed_lines) | set(s.removed_lines)
                if covered and any(f == _norm(s.file) and covered <= lines for f, lines in method_ranges if lines):
                    # Class entry fully covered by method entries: annotate scope, drop class dup
                    for m in method_syms:
                        if _norm(m.file) == _norm(s.file) and (set(m.changed_lines) | set(m.removed_lines)) >= covered:
                            m.enclosing = s.name
                            break
                    continue
            kept.append(s)
        else:
            kept.append(s)
    return kept


def summarize(parsed: ParseResult) -> Dict[str, Any]:
    """Compact hunk summary for metadata / LLM context (bounded)."""
    files = []
    for fd in parsed.files[:20]:
        files.append({
            "path": fd.path,
            "status": fd.status,
            "hunks": len(fd.hunks),
            "added": len(fd.added_lines),
            "removed": len(fd.removed_lines),
        })
    return {
        "files": len(parsed.files),
        "hunks": sum(len(fd.hunks) for fd in parsed.files),
        "added_lines": sum(len(fd.added_lines) for fd in parsed.files),
        "removed_lines": sum(len(fd.removed_lines) for fd in parsed.files),
        "truncated": parsed.truncated,
        "detail": files,
    }
