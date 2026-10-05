"""
DevLensX Go Language Adapter
Translates Tree-sitter Go CST to Universal Repository Model.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from tree_sitter import Node

from devlensx.urm.adapters.base import (
    BaseLanguageAdapter, SupportedLanguage, SymbolKind, RelationshipType,
    URMSymbol, URMRelationship, URMEndpoint, URMConfiguration, URMFramework,
    SourceLocation, ParseResult
)


class GoLanguageAdapter(BaseLanguageAdapter):
    """Go language adapter using Tree-sitter."""
    
    def __init__(self):
        super().__init__(SupportedLanguage.GO)
    
    def get_file_extensions(self) -> tuple:
        return (".go",)
        super().__init__(SupportedLanguage.GO)
        
        # Go node types
        self.STRUCT_TYPES = {"type_declaration"}
        self.INTERFACE_TYPES = {"interface_type"}
        self.FUNCTION_TYPES = {"function_declaration", "method_declaration"}
        self.VAR_TYPES = {"var_declaration", "const_declaration", "short_var_declaration"}
        self.IMPORT_TYPES = {"import_declaration", "import_spec"}
        self.CALL_TYPES = {"call_expression"}
    
    def extract_symbols(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Extract symbols from Go file."""
        symbols = []
        root = parse_result.root_node
        if not root:
            return symbols
        
        package_name = self._extract_package(root, parse_result)
        module_name = self._get_module_name(parse_result, package_name)
        
        # Extract imports
        imports = self._extract_imports(root, parse_result)
        
        # Type declarations (structs, interfaces, type aliases)
        for type_node in self._find_nodes_by_types(root, self.STRUCT_TYPES):
            type_symbols = self._extract_type_symbols(type_node, parse_result, module_name)
            symbols.extend(type_symbols)
        
        # Functions and methods
        for func_node in self._find_nodes_by_types(root, self.FUNCTION_TYPES):
            func_symbol = self._extract_function_symbol(func_node, parse_result, module_name, None)
            if func_symbol:
                symbols.append(func_symbol)
        
        # Variables and constants
        for var_node in self._find_nodes_by_types(root, self.VAR_TYPES):
            var_symbols = self._extract_var_symbols(var_node, parse_result, module_name)
            symbols.extend(var_symbols)
        
        return symbols
    
    def _extract_package(self, root: Node, parse_result: ParseResult) -> str:
        """Extract package declaration."""
        for child in root.children:
            if child.type == "package_clause":
                for c in child.children:
                    if c.type == "package_identifier":
                        return self._get_node_text(parse_result, c)
        return ""
    
    def _get_module_name(self, parse_result: ParseResult, package_name: str) -> str:
        """Get module name from file path or package."""
        path = Path(parse_result.file_path)
        if package_name:
            return package_name
        return path.stem
    
    def _extract_imports(self, root: Node, parse_result: ParseResult) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        for import_node in self._find_nodes_by_types(root, self.IMPORT_TYPES):
            if import_node.type == "import_declaration":
                for child in import_node.children:
                    if child.type == "import_spec":
                        path = ""
                        alias = None
                        for c in child.children:
                            if c.type == "interpreted_string_literal":
                                path = self._get_node_text(parse_result, c).strip('"')
                            elif c.type == "identifier":
                                alias = self._get_node_text(parse_result, c)
                        imports.append({"path": path, "alias": alias})
        return imports
    
    def _extract_type_symbols(self, type_node: Node, parse_result: ParseResult,
                              module_name: str) -> List[URMSymbol]:
        """Extract type declarations (structs, interfaces, aliases)."""
        symbols = []
        
        for child in type_node.children:
            if child.type == "type_spec":
                name_node = self._find_child_by_type(child, "type_identifier")
                if not name_node:
                    continue
                
                type_name = self._get_node_text(parse_result, name_node)
                location = self._create_location(parse_result, child)
                
                # Determine what kind of type
                type_def = None
                for c in child.children:
                    if c.type in ("struct_type", "interface_type", "type_identifier", 
                                 "array_type", "slice_type", "map_type", "pointer_type"):
                        type_def = c
                        break
                
                if type_def:
                    if type_def.type == "struct_type":
                        kind = SymbolKind.STRUCT
                        stereotype = self._classify_go_struct(type_name)
                    elif type_def.type == "interface_type":
                        kind = SymbolKind.INTERFACE
                        stereotype = "Interface"
                    else:
                        kind = SymbolKind.TYPE_ALIAS
                        stereotype = "TypeAlias"
                else:
                    kind = SymbolKind.TYPE_ALIAS
                    stereotype = "TypeAlias"
                
                symbols.append(URMSymbol(
                    id=self._generate_symbol_id(type_name, "go"),
                    name=type_name,
                    qualified_name=f"{module_name}.{type_name}",
                    kind=kind,
                    language="go",
                    location=location,
                    stereotype=stereotype,
                    metadata={"type_definition": self._get_node_text(parse_result, type_def) if type_def else ""},
                ))
        
        return symbols
    
    def _classify_go_struct(self, struct_name: str) -> str:
        """Classify Go struct based on naming conventions."""
        name_lower = struct_name.lower()
        if name_lower.endswith("service"):
            return "Service"
        elif name_lower.endswith("repository") or name_lower.endswith("repo") or name_lower.endswith("store"):
            return "Repository"
        elif name_lower.endswith("handler") or name_lower.endswith("controller"):
            return "Handler"
        elif name_lower.endswith("model") or name_lower.endswith("entity") or name_lower.endswith("dto"):
            return "Model"
        elif name_lower.endswith("config") or name_lower.endswith("configuration"):
            return "Configuration"
        elif name_lower.endswith("request") or name_lower.endswith("response"):
            return "RequestResponse"
        elif name_lower.endswith("error"):
            return "Error"
        return "Struct"
    
    def _extract_function_symbol(self, func_node: Node, parse_result: ParseResult,
                                 module_name: str, parent_type: Optional[URMSymbol]) -> Optional[URMSymbol]:
        """Extract function or method symbol."""
        name_node = self._find_child_by_type(func_node, "identifier")
        if not name_node:
            return None
        
        func_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, func_node)
        
        # Check if it's a method (has receiver)
        is_method = False
        receiver_type = ""
        for child in func_node.children:
            if child.type == "parameter_list":
                # First parameter might be receiver
                for c in child.children:
                    if c.type == "parameter_declaration":
                        # Check if it's a receiver (has no name, just type)
                        for cc in c.children:
                            if cc.type == "pointer_type" or cc.type == "type_identifier":
                                is_method = True
                                receiver_type = self._get_node_text(parse_result, cc)
                                break
        
        # Get parameters
        params = []
        return_types = []
        
        for child in func_node.children:
            if child.type == "parameter_list":
                for c in child.children:
                    if c.type == "parameter_declaration":
                        param_name = ""
                        param_type = ""
                        for cc in c.children:
                            if cc.type == "identifier":
                                param_name = self._get_node_text(parse_result, cc)
                            elif cc.type in ("type_identifier", "pointer_type", "slice_type", "map_type"):
                                param_type = self._get_node_text(parse_result, cc)
                        if param_name:
                            params.append({"name": param_name, "type": param_type})
            elif child.type == "result":
                for c in child.children:
                    if c.type == "parameter_list":
                        for cc in c.children:
                            if cc.type == "parameter_declaration":
                                for ccc in cc.children:
                                    if ccc.type in ("type_identifier", "pointer_type", "slice_type"):
                                        return_types.append(self._get_node_text(parse_result, ccc))
        
        param_str = ", ".join([f"{p['name']} {p['type']}" for p in params])
        return_str = ", ".join(return_types)
        signature = f"{func_name}({param_str})"
        if return_str:
            signature += f" ({return_str})"
        
        if is_method:
            kind = SymbolKind.METHOD
            stereotype = "Method"
            qualified_name = f"{module_name}.{receiver_type}.{func_name}" if receiver_type else f"{module_name}.{func_name}"
        else:
            kind = SymbolKind.FUNCTION
            # Check for HTTP handlers
            if func_name.lower().startswith("handle") or "handler" in func_name.lower():
                stereotype = "Handler"
            elif func_name == "main":
                stereotype = "Main"
            else:
                stereotype = "Function"
            qualified_name = f"{module_name}.{func_name}"
        
        return URMSymbol(
            id=self._generate_symbol_id(f"{receiver_type}_{func_name}" if is_method else func_name, "go"),
            name=func_name,
            qualified_name=qualified_name,
            kind=kind,
            language="go",
            location=location,
            signature=signature,
            stereotype=stereotype,
            metadata={
                "receiver_type": receiver_type,
                "parameters": params,
                "return_types": return_types,
                "is_method": is_method,
            },
        )
    
    def _extract_var_symbols(self, var_node: Node, parse_result: ParseResult,
                             module_name: str) -> List[URMSymbol]:
        """Extract variable/constant declarations."""
        symbols = []
        location = self._create_location(parse_result, var_node)
        
        is_const = var_node.type == "const_declaration"
        
        for child in var_node.children:
            if child.type == "var_spec" or child.type == "const_spec":
                for c in child.children:
                    if c.type == "identifier":
                        name = self._get_node_text(parse_result, c)
                        
                        # Get type if specified
                        var_type = ""
                        for cc in child.children:
                            if cc.type in ("type_identifier", "pointer_type", "slice_type", "map_type", "array_type"):
                                var_type = self._get_node_text(parse_result, cc)
                        
                        symbols.append(URMSymbol(
                            id=self._generate_symbol_id(name, "go"),
                            name=name,
                            qualified_name=f"{module_name}.{name}",
                            kind=SymbolKind.CONSTANT if is_const else SymbolKind.VARIABLE,
                            language="go",
                            location=location,
                            signature=var_type,
                            stereotype="Constant" if is_const else "Variable",
                        ))
        
        return symbols
    
    def extract_relationships(self, parse_result: ParseResult,
                              symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract relationships from Go file."""
        relationships = []
        root = parse_result.root_node
        if not root:
            return relationships
        
        symbol_by_name = {s.name: s for s in symbols}
        
        # Type embedding (struct embedding = composition)
        for type_node in self._find_nodes_by_types(root, self.STRUCT_TYPES):
            for child in type_node.children:
                if child.type == "type_spec":
                    name_node = self._find_child_by_type(child, "type_identifier")
                    if not name_node:
                        continue
                    type_name = self._get_node_text(parse_result, name_node)
                    
                    # Check for embedded fields (composition)
                    for c in child.children:
                        if c.type == "struct_type":
                            for field in c.children:
                                if field.type == "field_declaration":
                                    # Embedded field (no name, just type)
                                    field_type = ""
                                    for fc in field.children:
                                        if fc.type in ("type_identifier", "pointer_type"):
                                            field_type = self._get_node_text(parse_result, fc)
                                            break
                                    if field_type and field_type in symbol_by_name:
                                        relationships.append(URMRelationship(
                                            source_id=symbol_by_name[type_name].id,
                                            target_id=field_type,
                                            relationship_type=RelationshipType.CONTAINS,
                                            language="go",
                                        ))
        
        # Import relationships
        imports = self._extract_imports(root, parse_result)
        for symbol in symbols:
            for imp in imports:
                imp_path = imp.get("path", "")
                # Match imported packages to local symbols
                if imp_path:
                    # This would need package-level resolution
                    pass
        
        return relationships
    
    def extract_endpoints(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMEndpoint]:
        """Extract HTTP endpoints from Go handlers."""
        endpoints = []
        
        # Look for HTTP handler patterns
        for symbol in symbols:
            if symbol.stereotype in ("Handler", "Main"):
                # Check if it registers HTTP routes
                # This would need more context about the router used
                if "http" in str(symbol.metadata).lower():
                    endpoints.append(URMEndpoint(
                        route=f"/{symbol.name.lower()}",
                        http_method="GET",
                        handler_symbol_id=symbol.id,
                        framework="net/http / Gorilla Mux / Chi / Gin",
                        location=symbol.location,
                    ))
        
        return endpoints
    
    def extract_configuration(self, parse_result: ParseResult) -> List[URMConfiguration]:
        """Extract configuration from Go config files."""
        configs = []
        path = Path(parse_result.file_path)
        
        config_files = {
            "go.mod": "go_modules",
            "go.sum": "go_modules",
            "Makefile": "make",
            "Dockerfile": "docker",
            ".env": "env",
        }
        
        if path.name in config_files:
            config_type = config_files[path.name]
            
            if path.name == "go.mod":
                lines = parse_result.source_code.splitlines()
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line and not line.startswith("//"):
                        if line.startswith("module "):
                            configs.append(URMConfiguration(
                                file_path=parse_result.file_path,
                                config_type="go_module",
                                key="module",
                                value=line.replace("module ", "").strip(),
                                location=SourceLocation(
                                    file_path=parse_result.file_path,
                                    start_line=i + 1, start_column=1,
                                    end_line=i + 1, end_column=len(line) + 1,
                                ),
                            ))
                        elif "require" in line:
                            configs.append(URMConfiguration(
                                file_path=parse_result.file_path,
                                config_type="go_module",
                                key="require",
                                value=line.strip(),
                                location=SourceLocation(
                                    file_path=parse_result.file_path,
                                    start_line=i + 1, start_column=1,
                                    end_line=i + 1, end_column=len(line) + 1,
                                ),
                            ))
        
        return configs
    
    def extract_frameworks(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMFramework]:
        """Detect Go frameworks."""
        frameworks = []
        content = parse_result.source_code
        path = Path(parse_result.file_path)
        
        if path.name == "go.mod":
            framework_patterns = {
                "github.com/gin-gonic/gin": "Gin",
                "github.com/go-chi/chi": "Chi",
                "github.com/gorilla/mux": "Gorilla Mux",
                "github.com/labstack/echo": "Echo",
                "github.com/gin-contrib/": "Gin Middleware",
                "github.com/gofiber/fiber": "Fiber",
                "github.com/uber-go/fx": "Fx",
                "github.com/google/wire": "Wire",
                "github.com/spf13/cobra": "Cobra",
                "github.com/spf13/viper": "Viper",
                "github.com/jmoiron/sqlx": "SQLx",
                "gorm.io/gorm": "GORM",
                "github.com/jackc/pgx": "pgx",
                "github.com/redis/go-redis": "Go Redis",
                "github.com/segmentio/kafka-go": "Kafka Go",
                "github.com/nats-io/nats.go": "NATS Go",
                "github.com/grpc/grpc-go": "gRPC Go",
                "google.golang.org/grpc": "gRPC Go",
                "github.com/uber/jaeger-client-go": "Jaeger",
                "github.com/prometheus/client_golang": "Prometheus",
            }
            
            for pattern, framework in framework_patterns.items():
                if pattern in content:
                    frameworks.append(URMFramework(
                        name=framework,
                        language="go",
                        evidence_files=[parse_result.file_path],
                    ))
        
        # Check for standard library frameworks
        if "net/http" in content:
            frameworks.append(URMFramework(
                name="net/http",
                language="go",
                evidence_files=[parse_result.file_path],
            ))
        
        return frameworks


