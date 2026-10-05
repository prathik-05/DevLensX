from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class ChangeType(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    UNCHANGED = "UNCHANGED"

@dataclass
class FileChange:
    path: str
    change_type: ChangeType
    old_path: Optional[str] = None
    new_path: Optional[str] = None

    def to_dict(self):
        return {"path": self.path, "change_type": self.change_type.value, "old_path": self.old_path, "new_path": self.new_path}

@dataclass
class SymbolChange:
    symbol_id: str
    file_path: str
    change_type: ChangeType
    symbol_name: str = ""
    is_test: bool = False

    def to_dict(self):
        return {"symbol_id": self.symbol_id, "file_path": self.file_path, "change_type": self.change_type.value, "symbol_name": self.symbol_name}

@dataclass
class InvalidationSet:
    files: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    diagrams: List[str] = field(default_factory=list)
    wiki_pages: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    vectors: List[str] = field(default_factory=list)

    def to_dict(self):
        return {"files": self.files, "symbols": self.symbols, "relationships": self.relationships, "diagrams": self.diagrams, "wiki_pages": self.wiki_pages, "evidence": self.evidence, "vectors": self.vectors}

@dataclass
class IncrementalResult:
    repository_id: str
    previous_run_id: str
    new_run_id: str
    previous_commit: Optional[str]
    new_commit: Optional[str]
    changed_files: List[FileChange] = field(default_factory=list)
    changed_symbols: List[SymbolChange] = field(default_factory=list)
    invalidated_artifacts: InvalidationSet = field(default_factory=InvalidationSet)
    rebuilt_artifacts: InvalidationSet = field(default_factory=InvalidationSet)
    status: str = "COMPLETE"

    def to_dict(self):
        return {
            "repository_id": self.repository_id,
            "previous_analysis_run_id": self.previous_run_id,
            "analysis_run_id": self.new_run_id,
            "previous_commit_hash": self.previous_commit,
            "commit_hash": self.new_commit,
            "changed_files": [f.to_dict() for f in self.changed_files],
            "changed_symbols": [s.to_dict() for s in self.changed_symbols],
            "invalidated_artifacts": self.invalidated_artifacts.to_dict(),
            "rebuilt_artifacts": self.rebuilt_artifacts.to_dict(),
            "status": self.status,
        }
