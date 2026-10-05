"""Review diff analyzer — hunk-level changed-file/symbol mapping (P1-B).

Backward-compatible surface:
  changed_files(diff) -> List[str]
  changed_symbols(diff, model) -> List[model dicts] (with `diff_change` attached)

New surface:
  parse(diff) -> ParseResult (hunks, statuses, truncation diagnostics)
  resolve(diff, model) -> List[ChangedSymbol] (range-contained, innermost)
"""

from typing import Dict, Any, List

from devlensx.review.hunks import HunkParser, ParseResult
from devlensx.review.symbol_resolver import resolve_changed_symbols, ChangedSymbol


class DiffAnalyzer:
    @staticmethod
    def parse(diff: str) -> ParseResult:
        return HunkParser.parse(diff or "")

    @staticmethod
    def changed_files(diff: str) -> List[str]:
        parsed = HunkParser.parse(diff or "")
        return list(dict.fromkeys(fd.path for fd in parsed.files if fd.path))

    @staticmethod
    def resolve(diff: str, model: Dict[str, Any]) -> List[ChangedSymbol]:
        parsed = HunkParser.parse(diff or "")
        return resolve_changed_symbols(parsed, model or {})

    @staticmethod
    def changed_symbols(diff: str, model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Model symbol dicts touched by the diff (range-contained).

        Each returned dict is a shallow copy of the model entry with an
        attached `diff_change` payload: {change, changed_lines,
        removed_lines, enclosing, evidence_kind}. Callers that only need
        identity (name/file) work unchanged.
        """
        model = model or {}
        by_name = {c.get("name"): c for c in model.get("classes", []) if isinstance(c, dict)}
        out: List[Dict[str, Any]] = []
        for cs in DiffAnalyzer.resolve(diff, model):
            base = dict(by_name.get(cs.name, {"name": cs.name, "file": cs.file}))
            base["diff_change"] = {
                "change": cs.change,
                "changed_lines": cs.changed_lines,
                "removed_lines": cs.removed_lines,
                "enclosing": cs.enclosing,
                "evidence_kind": cs.evidence_kind,
            }
            out.append(base)
        return out
