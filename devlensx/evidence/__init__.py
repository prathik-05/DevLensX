"""
DevLensX Evidence Subsystem (D5)

Identity-bound source navigation:
    citation string -> EvidenceRef (full snapshot identity) -> ResolvedEvidence
"""

from devlensx.evidence.models import (
    EvidenceRef,
    EvidenceType,
    ResolutionStatus,
    ResolvedEvidence,
    SnapshotRecord,
    SourceLine,
)
from devlensx.evidence.citation import (
    build_citation,
    parse_citation,
    split_citation_range,
    ParsedCitation,
)
from devlensx.evidence.resolver import (
    EvidenceResolver,
    SnapshotRegistry,
    get_evidence_resolver,
    get_snapshot_registry,
    register_snapshot,
)
from devlensx.evidence.source_reader import SourceReader

__all__ = [
    "EvidenceRef", "EvidenceType", "ResolutionStatus", "ResolvedEvidence",
    "SnapshotRecord", "SourceLine",
    "build_citation", "parse_citation", "split_citation_range", "ParsedCitation",
    "EvidenceResolver", "SnapshotRegistry",
    "get_evidence_resolver", "get_snapshot_registry", "register_snapshot",
    "SourceReader",
]