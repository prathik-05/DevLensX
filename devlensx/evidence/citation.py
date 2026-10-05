"""
DevLensX Evidence Citations (D5)

Parsing and construction of citation strings such as:

    src/main/java/.../OwnerController.java#L23-L45

A citation string alone is NOT sufficient to resolve evidence — it must be
paired with snapshot identity (repository_id, analysis_run_id, commit_hash)
to form an EvidenceRef.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

_CITATION_RE = re.compile(
    r"^(?P<path>.+?)#L(?P<start>\d+)(?:-L?(?P<end>\d+))?$",
    re.IGNORECASE,
)


@dataclass
class ParsedCitation:
    file_path: str
    line_start: int
    line_end: int


def build_citation(file_path: str, line_start: int, line_end: Optional[int] = None) -> str:
    """Builds a canonical citation string."""
    end = line_end if line_end is not None and line_end >= line_start else line_start
    return f"{file_path}#L{line_start}-L{end}"


def parse_citation(citation: str) -> Optional[ParsedCitation]:
    """Parses 'path#L10' or 'path#L10-L20'. Returns None when malformed."""
    if not citation:
        return None
    match = _CITATION_RE.match(citation.strip())
    if not match:
        return None
    start = int(match.group("start"))
    end_raw = match.group("end")
    end = int(end_raw) if end_raw else start
    if end < start:
        start, end = end, start
    path = match.group("path").replace("\\", "/")
    if not path or path.startswith("/"):
        return None
    return ParsedCitation(file_path=path, line_start=start, line_end=end)


def citation_from_symbol(
    file_path: str,
    line_start: int,
    line_end,
) -> str:
    """Convenience wrapper tolerant of missing/None line_end values."""
    try:
        end = int(line_end)
    except (TypeError, ValueError):
        end = int(line_start)
    return build_citation(file_path, int(line_start), end)


def split_citation_range(citation: str) -> Optional[Tuple[str, int, int]]:
    parsed = parse_citation(citation)
    if parsed is None:
        return None
    return (parsed.file_path, parsed.line_start, parsed.line_end)