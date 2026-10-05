"""
DevLensX Universal Repository Model - Language Adapter Contracts
Defines the interface all language adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from devlensx.shared.types import SupportedLanguage, ParseResult
from tree_sitter import Node


class SymbolKind(str, Enum):
    """Universal symbol kinds across all languages."""
    MODULE = "MODULE"
    PACKAGE = "PACKAGE"
    NAMESPACE = "NAMESPACE"
    CLASS = "CLASS"
    INTERFACE = "INTERFACE"
    TRAIT = "TRAIT"
    STRUCT = "STRUCT"
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
    """Universal relationship types across all languages."""
    CONTAINS = "CONTAINS"           # Module/package contains symbol
    DEFINES = "DEFINES"             # File defines symbol
    EXTENDS = "EXTENDS"             # Class extends class
    IMPLEMENTS = "IMPLEMENTS"       # Class implements interface
    IMPORTS = "IMPORTS"             # File imports symbol
    CALLS = "CALLS"                 # Function calls function
    INSTANTIATES = "INSTANTIATES"   # Code instantiates class
    INHERITS = "INHERITS"           # Generic inheritance
    DEPENDS_ON = "DEPENDS_ON"       # Generic dependency
    RETURNS = "RETURNS"             # Function returns type
    ACCEPTS = "ACCEPTS"             # Function accepts parameter
    THROWS = "THROWS"               # Function throws exception
    DECORATES = "DECORATES"         # Decorator decorates target
    ANNOTATES = "ANNOTATES"         # Annotation annotates target
    ROUTES_TO = "ROUTES_TO"         # Route handler maps to path
    CONFIGURES = "CONFIGURES"       # Configuration configures target


@dataclass
class SourceLocation:
    """Source code location with line/column info."""
    file_path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "start_line": self.start_line,
            "start_column": self.start_column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }
    
    @property
    def line_range(self) -> str:
        return f"{self.start_line}-{self.end_line}"
    
    @property
    def citation_str(self) -> str:
        return f"{self.file_path}#L{self.start_line}-{self.end_line}"


@dataclass
class URMSymbol:
    """Universal Repository Model symbol - language-agnostic."""
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


@dataclass
class URMRelationship:
    """Universal Repository Model relationship - language-agnostic."""
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    language: str
    location: Optional[SourceLocation] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class URMEndpoint:
    """API endpoint / route definition."""
    route: str
    http_method: str
    handler_symbol_id: str
    framework: str
    location: SourceLocation
    middleware: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    response_type: Optional[str] = None


@dataclass
class URMConfiguration:
    """Configuration file entry."""
    file_path: str
    config_type: str  # json, yaml, toml, properties, xml, env, dockerfile
    key: str
    value: Any
    location: SourceLocation
    is_secret: bool = False


@dataclass
class URMFramework:
    """Detected framework information."""
    name: str
    language: str
    version: Optional[str] = None
    evidence_files: List[str] = field(default_factory=list)
    evidence_symbols: List[str] = field(default_factory=list)


@dataclass
class UniversalRepositoryModel:
    """Complete Universal Repository Model for a repository."""
    repository_id: str
    name: str
    root_path: str
    primary_language: str
    languages: Dict[str, float] = field(default_factory=dict)  # language -> percentage
    symbols: List[URMSymbol] = field(default_factory=list)
    relationships: List[URMRelationship] = field(default_factory=list)
    endpoints: List[URMEndpoint] = field(default_factory=list)
    configurations: List[URMConfiguration] = field(default_factory=list)
    frameworks: List[URMFramework] = field(default_factory=list)
    parse_errors: List[Dict[str, Any]] = field(default_factory=list)
    files_parsed: int = 0
    files_failed: int = 0


class BaseLanguageAdapter(ABC):
    """Base class for all language adapters.
    
    Each adapter translates Tree-sitter CST nodes into URM symbols/relationships.
    """
    
    def __init__(self, language: SupportedLanguage):
        self.language = language
        self._symbol_id_counter = 0
    
    def can_parse(self, file_path: str) -> bool:
        """Check if this adapter can parse the given file."""
        return file_path.endswith(self.get_file_extensions())
    
    def get_file_extensions(self) -> tuple:
        """Get file extensions this adapter handles. Override in subclasses."""
        return ()
    
    def parse_file(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Parse a file and extract symbols. Delegates to extract_symbols."""
        return self.extract_symbols(parse_result)
    
    @abstractmethod
    def extract_symbols(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Extract all symbols from a parsed file."""
        pass
    
    @abstractmethod
    def extract_relationships(self, parse_result: ParseResult, 
                              symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract relationships between symbols."""
        pass
    
    @abstractmethod
    def extract_endpoints(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMEndpoint]:
        """Extract API endpoints/routes."""
        pass
    
    @abstractmethod
    def extract_configuration(self, parse_result: ParseResult) -> List[URMConfiguration]:
        """Extract configuration from config files."""
        pass
    
    def extract_frameworks(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMFramework]:
        """Detect frameworks used in the file."""
        return []
    
    def _generate_symbol_id(self, name: str, prefix: str = "") -> str:
        """Generate unique symbol ID."""
        self._symbol_id_counter += 1
        prefix = prefix or self.language.value
        return f"{prefix}_{name}_{self._symbol_id_counter}"
    
    def _create_location(self, parse_result: ParseResult, node: Node) -> SourceLocation:
        """Create SourceLocation from Tree-sitter node."""
        return SourceLocation(
            file_path=parse_result.file_path,
            start_line=node.start_point[0] + 1,  # Tree-sitter is 0-indexed
            start_column=node.start_point[1],
            end_line=node.end_point[0] + 1,
            end_column=node.end_point[1],
        )
    
    def _get_node_text(self, parse_result: ParseResult, node: Node) -> str:
        """Get source text for a node."""
        if parse_result.source_code:
            return parse_result.source_code[node.start_byte:node.end_byte]
        return ""
    
    def _get_node_text_from_source(self, node: Node) -> str:
        """Get source text for a node from its text attribute (fallback when parse_result not available)."""
        if hasattr(node, 'text') and node.text:
            return node.text.decode('utf-8', errors='ignore') if isinstance(node.text, bytes) else str(node.text)
        return ""
    
    def _find_child_by_type(self, node: Node, *types: str) -> Optional[Node]:
        """Find first child matching any of the given types."""
        for child in node.children:
            if child.type in types:
                return child
        return None
    
    def _find_all_children_by_type(self, node: Node, *types: str) -> List[Node]:
        """Find all children matching any of the given types."""
        return [child for child in node.children if child.type in types]
    
    def _find_nodes_by_types(self, node: Node, *types: str) -> List[Node]:
        """Find all descendant nodes matching any of the given types (recursive).
        
        Can be called with either multiple string arguments or a single iterable:
            _find_nodes_by_types(node, "type1", "type2")
            _find_nodes_by_types(node, {"type1", "type2"})
        """
        # Handle both cases: multiple string args or single iterable
        if len(types) == 1 and not isinstance(types[0], str):
            # Single iterable argument (set, list, etc.)
            type_set = set(types[0])
        else:
            # Multiple string arguments
            type_set = set(types)
        
        results = []
        if node.type in type_set:
            results.append(node)
        for child in node.children:
            results.extend(self._find_nodes_by_types(child, type_set))
        return results


class AdapterRegistry:
    """Registry for language adapters."""
    
    def __init__(self):
        self._adapters: Dict[SupportedLanguage, BaseLanguageAdapter] = {}
    
    def register(self, adapter: BaseLanguageAdapter):
        """Register an adapter for its language."""
        self._adapters[adapter.language] = adapter
    
    def get(self, language: SupportedLanguage) -> Optional[BaseLanguageAdapter]:
        """Get adapter for a language."""
        return self._adapters.get(language)
    
    def get_all(self) -> List[BaseLanguageAdapter]:
        """Get all registered adapters."""
        return list(self._adapters.values())
    
    def supported_languages(self) -> List[SupportedLanguage]:
        """Get list of supported languages."""
        return list(self._adapters.keys())
    
    def process_parse_result(self, parse_result: ParseResult) -> Dict[str, Any]:
        """Process a parse result through the appropriate adapter."""
        adapter = self.get(parse_result.language)
        if not adapter or not parse_result.success:
            return {
                "symbols": [],
                "relationships": [],
                "endpoints": [],
                "configurations": [],
                "frameworks": [],
            }
        
        symbols = adapter.extract_symbols(parse_result)
        relationships = adapter.extract_relationships(parse_result, symbols)
        endpoints = adapter.extract_endpoints(parse_result, symbols)
        configurations = adapter.extract_configuration(parse_result)
        frameworks = adapter.extract_frameworks(parse_result, symbols)
        
        return {
            "symbols": symbols,
            "relationships": relationships,
            "endpoints": endpoints,
            "configurations": configurations,
            "frameworks": frameworks,
        }


# Global registry
_adapter_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get global adapter registry."""
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
    return _adapter_registry