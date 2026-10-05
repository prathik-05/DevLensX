"""
DevLensX Universal Repository Model (URM) Data Schemas
Language-agnostic AST and Graph Representation for Multi-Language Repositories.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class SymbolKind(str, Enum):
    MODULE = "MODULE"
    PACKAGE = "PACKAGE"
    NAMESPACE = "NAMESPACE"
    CLASS = "CLASS"
    STRUCT = "STRUCT"
    INTERFACE = "INTERFACE"
    TRAIT = "TRAIT"
    ENUM = "ENUM"
    TYPE_ALIAS = "TYPE_ALIAS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    CONSTRUCTOR = "CONSTRUCTOR"
    FIELD = "FIELD"
    PROPERTY = "PROPERTY"
    VARIABLE = "VARIABLE"
    CONSTANT = "CONSTANT"
    PARAMETER = "PARAMETER"
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    ANNOTATION = "ANNOTATION"
    DECORATOR = "DECORATOR"
    GENERIC_PARAM = "GENERIC_PARAM"


class RelationshipType(str, Enum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    DEPENDS_ON = "DEPENDS_ON"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    CONTAINS = "CONTAINS"
    DEFINES = "DEFINES"
    REFERENCES = "REFERENCES"
    RETURNS = "RETURNS"
    ACCEPTS = "ACCEPTS"
    THROWS = "THROWS"
    DECORATES = "DECORATES"
    ANNOTATES = "ANNOTATES"
    ROUTES_TO = "ROUTES_TO"
    CONFIGURES = "CONFIGURES"


@dataclass
class SourceLocation:
    file_path: str
    start_line: int
    start_column: int = 1
    end_line: int = 1
    end_column: int = 1
    
    @property
    def citation_str(self) -> str:
        return f"{self.file_path}#L{self.start_line}-{self.end_line}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "start_line": self.start_line,
            "start_column": self.start_column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


@dataclass
class SourceEvidence:
    source_type: str = "AST"  # AST, Graph, Git, Vector
    location: Optional[SourceLocation] = None
    parser: str = "tree-sitter"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "location": self.location.to_dict() if self.location else None,
            "parser": self.parser,
        }


@dataclass
class URMSymbol:
    id: str
    name: str
    qualified_name: str
    kind: SymbolKind
    language: str
    location: SourceLocation
    stereotype: Optional[str] = None
    signature: Optional[str] = None
    doc_comment: Optional[str] = None
    visibility: Optional[str] = None  # public, private, protected, internal
    is_static: bool = False
    is_async: bool = False
    is_abstract: bool = False
    is_final: bool = False
    generics: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    evidence: Optional[SourceEvidence] = None
    
    @property
    def file(self) -> str:
        return self.location.file_path if self.location else ""
    
    @property
    def line_start(self) -> int:
        return self.location.start_line if self.location else 1
    
    @property
    def line_end(self) -> int:
        return self.location.end_line if self.location else 1
    
    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to legacy dictionary format for backward compatibility."""
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "kind": self.kind.value.lower() if hasattr(self.kind, 'value') else str(self.kind).lower(),
            "stereotype": self.stereotype or "Class",
            "file": self.file,
            "package": self._extract_package(),
            "line_start": self.line_start,
            "line_end": self.line_end,
            "language": self.language,
            "signature": self.signature,
            "annotations": self.annotations,
            "modifiers": self.modifiers,
            "is_static": self.is_static,
            "is_async": self.is_async,
            "generics": self.generics,
            "metadata": self.metadata,
        }
    
    def _extract_package(self) -> str:
        """Extract package/namespace from qualified name."""
        parts = self.qualified_name.split(".")
        if len(parts) > 1:
            return ".".join(parts[:-1])
        parts = self.qualified_name.split("::")
        if len(parts) > 1:
            return "::".join(parts[:-1])
        return ""


@dataclass
class URMRelationship:
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    language: str
    location: Optional[SourceLocation] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class URMEndpoint:
    route: str
    http_method: str
    handler_symbol_id: str
    framework: str
    location: SourceLocation
    middleware: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    response_type: Optional[str] = None
    
    @property
    def file(self) -> str:
        return self.location.file_path
    
    @property
    def line(self) -> int:
        return self.location.start_line


@dataclass
class URMConfiguration:
    file_path: str
    config_type: str  # json, yaml, toml, properties, xml, env, dockerfile, cmake, cargo, go_module
    key: str
    value: Any
    location: SourceLocation
    is_secret: bool = False


@dataclass
class URMFramework:
    name: str
    language: str
    version: Optional[str] = None
    evidence_files: List[str] = field(default_factory=list)
    evidence_symbols: List[str] = field(default_factory=list)


@dataclass
class UniversalRepositoryModel:
    repository_id: str
    name: str
    root_path: str
    primary_language: str
    languages: Dict[str, float] = field(default_factory=dict)  # language -> percentage
    frameworks: List[URMFramework] = field(default_factory=list)
    symbols: List[URMSymbol] = field(default_factory=list)
    relationships: List[URMRelationship] = field(default_factory=list)
    endpoints: List[URMEndpoint] = field(default_factory=list)
    configurations: List[URMConfiguration] = field(default_factory=list)
    
    # Convenience properties
    @property
    def classes(self) -> List[URMSymbol]:
        return [s for s in self.symbols if s.kind in (SymbolKind.CLASS, SymbolKind.STRUCT, SymbolKind.INTERFACE, SymbolKind.ENUM, SymbolKind.TRAIT)]
    
    @property
    def functions(self) -> List[URMSymbol]:
        return [s for s in self.symbols if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD, SymbolKind.CONSTRUCTOR)]
    
    @property
    def by_language(self) -> Dict[str, List[URMSymbol]]:
        result = {}
        for s in self.symbols:
            if s.language not in result:
                result[s.language] = []
            result[s.language].append(s)
        return result
    
    @property
    def by_kind(self) -> Dict[SymbolKind, List[URMSymbol]]:
        result = {}
        for s in self.symbols:
            if s.kind not in result:
                result[s.kind] = []
            result[s.kind].append(s)
        return result