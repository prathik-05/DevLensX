"""
DevLensX C++ Language Adapter
Translates Tree-sitter C++ CST to Universal Repository Model.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from tree_sitter import Node

from devlensx.urm.adapters.base import (
    BaseLanguageAdapter, SupportedLanguage, SymbolKind, RelationshipType,
    URMSymbol, URMRelationship, URMEndpoint, URMConfiguration, URMFramework,
    SourceLocation, ParseResult
)


class CppLanguageAdapter(BaseLanguageAdapter):
    """C++ language adapter using Tree-sitter."""
    
    def __init__(self):
        super().__init__(SupportedLanguage.CPP)
    
    def get_file_extensions(self) -> tuple:
        return (".cpp", ".cc", ".cxx", ".hpp", ".h", ".c")
        super().__init__(SupportedLanguage.CPP)
        
        # C++ node types
        self.CLASS_TYPES = {"class_specifier", "struct_specifier"}
        self.ENUM_TYPES = {"enum_specifier"}
        self.FUNCTION_TYPES = {"function_definition", "function_declarator"}
        self.METHOD_TYPES = {"function_definition"}  # Methods are functions inside classes
        self.FIELD_TYPES = {"field_declaration"}
        self.NAMESPACE_TYPES = {"namespace_definition"}
        self.INCLUDE_TYPES = {"preproc_include"}
        self.TEMPLATE_TYPES = {"template_declaration"}
        self.TYPEDEF_TYPES = {"type_definition"}
        self.USING_TYPES = {"using_declaration"}
    
    def extract_symbols(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Extract symbols from C++ file."""
        symbols = []
        root = parse_result.root_node
        if not root:
            return symbols
        
        module_name = self._get_module_name(parse_result)
        
        # Extract includes
        includes = self._extract_includes(root, parse_result)
        
        # Namespaces
        for ns_node in self._find_nodes_by_types(root, self.NAMESPACE_TYPES):
            ns_symbols = self._extract_namespace_symbols(ns_node, parse_result, module_name)
            symbols.extend(ns_symbols)
        
        # Classes and structs (at global scope)
        for class_node in self._find_nodes_by_types(root, self.CLASS_TYPES):
            # Only top-level classes (not nested)
            parent = class_node.parent
            if parent and parent.type not in self.CLASS_TYPES:
                class_symbols = self._extract_class_symbols(class_node, parse_result, module_name)
                symbols.extend(class_symbols)
        
        # Enums (top-level)
        for enum_node in self._find_nodes_by_types(root, self.ENUM_TYPES):
            parent = enum_node.parent
            if parent and parent.type not in self.CLASS_TYPES:
                enum_symbol = self._extract_enum_symbol(enum_node, parse_result, module_name)
                if enum_symbol:
                    symbols.append(enum_symbol)
        
        # Functions (top-level)
        for func_node in self._find_nodes_by_types(root, self.FUNCTION_TYPES):
            parent = func_node.parent
            if parent and parent.type not in self.CLASS_TYPES:
                func_symbol = self._extract_function_symbol(func_node, parse_result, module_name, None)
                if func_symbol:
                    symbols.append(func_symbol)
        
        # Typedefs and using
        for typedef_node in self._find_nodes_by_types(root, self.TYPEDEF_TYPES):
            typedef_symbol = self._extract_typedef_symbol(typedef_node, parse_result, module_name)
            if typedef_symbol:
                symbols.append(typedef_symbol)
        
        for using_node in self._find_nodes_by_types(root, self.USING_TYPES):
            using_symbol = self._extract_using_symbol(using_node, parse_result, module_name)
            if using_symbol:
                symbols.append(using_symbol)
        
        return symbols
    
    def _get_module_name(self, parse_result: ParseResult) -> str:
        """Get module name from file path."""
        path = Path(parse_result.file_path)
        return path.stem
    
    def _extract_includes(self, root: Node, parse_result: ParseResult) -> List[str]:
        """Extract include directives."""
        includes = []
        for include_node in self._find_nodes_by_types(root, self.INCLUDE_TYPES):
            for child in include_node.children:
                if child.type in ("string_literal", "system_lib_string"):
                    includes.append(self._get_node_text(parse_result, child).strip('<>"'))
        return includes
    
    def _extract_namespace_symbols(self, ns_node: Node, parse_result: ParseResult,
                                   parent_module: str) -> List[URMSymbol]:
        """Extract symbols from namespace."""
        symbols = []
        
        # Get namespace name
        ns_name = ""
        for child in ns_node.children:
            if child.type == "identifier":
                ns_name = self._get_node_text(parse_result, child)
                break
        
        module_name = f"{parent_module}::{ns_name}" if ns_name else parent_module
        
        # Extract symbols inside namespace
        for child in ns_node.children:
            if child.type == "declaration_list":
                for item in child.children:
                    if child.type in self.CLASS_TYPES:
                        class_symbols = self._extract_class_symbols(item, parse_result, module_name)
                        symbols.extend(class_symbols)
                    elif child.type in self.ENUM_TYPES:
                        enum_symbol = self._extract_enum_symbol(item, parse_result, module_name)
                        if enum_symbol:
                            symbols.append(enum_symbol)
                    elif child.type in self.FUNCTION_TYPES:
                        func_symbol = self._extract_function_symbol(item, parse_result, module_name, None)
                        if func_symbol:
                            symbols.append(func_symbol)
        
        return symbols
    
    def _extract_class_symbols(self, class_node: Node, parse_result: ParseResult,
                               module_name: str) -> List[URMSymbol]:
        """Extract class/struct and its members."""
        symbols = []
        
        # Get class name
        name_node = None
        for child in class_node.children:
            if child.type == "type_identifier":
                name_node = child
                break
        
        if not name_node:
            return symbols
        
        class_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, class_node)
        
        # Determine if class or struct
        is_struct = class_node.type == "struct_specifier"
        kind = SymbolKind.STRUCT if is_struct else SymbolKind.CLASS
        base_stereotype = "Struct" if is_struct else "Class"
        
        # Get base classes
        base_classes = []
        for child in class_node.children:
            if child.type == "base_class_clause":
                for c in child.children:
                    if c.type == "type_identifier":
                        base_classes.append(self._get_node_text(parse_result, c))
        
        # Get template parameters
        template_params = []
        parent = class_node.parent
        if parent and parent.type == "template_declaration":
            for child in parent.children:
                if child.type == "template_parameter_list":
                    for c in child.children:
                        if c.type == "template_type_parameter":
                            for cc in c.children:
                                if cc.type == "identifier":
                                    template_params.append(self._get_node_text(parse_result, cc))
        
        stereotype = self._classify_cpp_class(class_name, base_classes, is_struct)
        
        class_symbol = URMSymbol(
            id=self._generate_symbol_id(class_name, "cpp"),
            name=class_name,
            qualified_name=f"{module_name}::{class_name}",
            kind=kind,
            language="cpp",
            location=location,
            stereotype=stereotype,
            generics=template_params,
            metadata={
                "base_classes": base_classes,
                "is_struct": is_struct,
                "template_params": template_params,
            },
        )
        symbols.append(class_symbol)
        
        # Extract class members
        for child in class_node.children:
            if child.type == "field_declaration_list":
                for member in child.children:
                    if member.type == "field_declaration":
                        field_symbols = self._extract_field_symbols(member, parse_result, class_symbol, module_name)
                        symbols.extend(field_symbols)
                    elif member.type == "function_definition":
                        method_symbol = self._extract_method_symbol(member, parse_result, class_symbol, module_name)
                        if method_symbol:
                            symbols.append(method_symbol)
                    elif member.type == "access_specifier":
                        # Track access level for subsequent members
                        pass
        
        return symbols
    
    def _classify_cpp_class(self, class_name: str, base_classes: List[str], is_struct: bool) -> str:
        """Classify C++ class/struct."""
        name_lower = class_name.lower()
        
        if name_lower.endswith("service"):
            return "Service"
        elif name_lower.endswith("repository") or name_lower.endswith("repo"):
            return "Repository"
        elif name_lower.endswith("handler") or name_lower.endswith("controller"):
            return "Handler"
        elif name_lower.endswith("manager"):
            return "Manager"
        elif name_lower.endswith("factory"):
            return "Factory"
        elif name_lower.endswith("builder"):
            return "Builder"
        elif name_lower.endswith("context"):
            return "Context"
        elif name_lower.endswith("config") or name_lower.endswith("settings"):
            return "Configuration"
        elif name_lower.endswith("model") or name_lower.endswith("entity"):
            return "Model"
        elif name_lower.endswith("exception") or name_lower.endswith("error"):
            return "Exception"
        elif name_lower.endswith("test"):
            return "Test"
        elif name_lower.endswith("impl") or name_lower.endswith("implementation"):
            return "Implementation"
        
        # Check base classes
        for base in base_classes:
            base_lower = base.lower()
            if "service" in base_lower:
                return "Service"
            elif "repository" in base_lower:
                return "Repository"
            elif "handler" in base_lower:
                return "Handler"
        
        return "Struct" if is_struct else "Class"
    
    def _extract_field_symbols(self, field_node: Node, parse_result: ParseResult,
                               parent_class: URMSymbol, module_name: str) -> List[URMSymbol]:
        """Extract field/method symbols from class body."""
        symbols = []
        location = self._create_location(parse_result, field_node)
        
        for child in field_node.children:
            if child.type == "field_declaration":
                # Member variable
                field_type = ""
                field_name = ""
                
                for c in child.children:
                    if c.type in ("type_identifier", "generic_type", "reference_type", "pointer_type"):
                        field_type = self._get_node_text(parse_result, c)
                    elif c.type == "field_identifier":
                        field_name = self._get_node_text(parse_result, c)
                
                if field_name:
                    symbols.append(URMSymbol(
                        id=self._generate_symbol_id(f"{parent_class.name}_{field_name}", "cpp"),
                        name=field_name,
                        qualified_name=f"{parent_class.qualified_name}::{field_name}",
                        kind=SymbolKind.FIELD,
                        language="cpp",
                        location=location,
                        signature=field_type,
                        stereotype="Field",
                        metadata={"parent_class": parent_class.id, "field_type": field_type},
                    ))
            
            elif child.type == "function_definition":
                # Method
                method_symbol = self._extract_method_symbol(child, parse_result, parent_class, module_name)
                if method_symbol:
                    symbols.append(method_symbol)
        
        return symbols
    
    def _extract_method_symbol(self, method_node: Node, parse_result: ParseResult,
                               parent_class: URMSymbol, module_name: str) -> Optional[URMSymbol]:
        """Extract method symbol from class."""
        # Get declarator
        declarator = None
        for child in method_node.children:
            if child.type == "function_declarator":
                declarator = child
                break
        
        if not declarator:
            return None
        
        # Get method name
        name_node = None
        for child in declarator.children:
            if child.type == "identifier":
                name_node = child
                break
        
        if not name_node:
            return None
        
        method_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, method_node)
        
        # Get parameters
        params = []
        for child in declarator.children:
            if child.type == "parameter_list":
                for param in child.children:
                    if child.type == "parameter_declaration":
                        param_name = ""
                        param_type = ""
                        for pc in param.children:
                            if pc.type == "identifier":
                                param_name = self._get_node_text(parse_result, pc)
                            elif pc.type in ("type_identifier", "generic_type", "reference_type", "pointer_type"):
                                param_type = self._get_node_text(parse_result, pc)
                        if param_name:
                            params.append({"name": param_name, "type": param_type})
        
        # Get return type
        return_type = ""
        for child in method_node.children:
            if child.type in ("type_identifier", "generic_type", "reference_type", "void_type"):
                # Check if it's before declarator (return type)
                if child.start_byte < declarator.start_byte:
                    return_type = self._get_node_text(parse_result, child)
        
        param_str = ", ".join([f"{p['type']} {p['name']}" for p in params])
        signature = f"{return_type} {method_name}({param_str})" if return_type else f"{method_name}({param_str})"
        
        # Check for virtual/override/static
        is_virtual = False
        is_override = False
        is_static = False
        for child in method_node.children:
            if child.type in ("virtual", "override", "static"):
                if child.type == "virtual":
                    is_virtual = True
                elif child.type == "override":
                    is_override = True
                elif child.type == "static":
                    is_static = True
        
        stereotype = "Method"
        if method_name == parent_class.name:
            stereotype = "Constructor"
        elif method_name == f"~{parent_class.name}":
            stereotype = "Destructor"
        elif is_static:
            stereotype = "StaticMethod"
        
        qualified_name = f"{parent_class.qualified_name}::{method_name}"
        
        return URMSymbol(
            id=self._generate_symbol_id(f"{parent_class.name}_{method_name}", "cpp"),
            name=method_name,
            qualified_name=qualified_name,
            kind=SymbolKind.METHOD,
            language="cpp",
            location=location,
            signature=signature,
            stereotype=stereotype,
            is_static=is_static,
            metadata={
                "parent_class": parent_class.id,
                "parameters": params,
                "return_type": return_type,
                "is_virtual": is_virtual,
                "is_override": is_override,
                "is_constructor": method_name == parent_class.name,
                "is_destructor": method_name == f"~{parent_class.name}",
            },
        )
    
    def _extract_enum_symbol(self, enum_node: Node, parse_result: ParseResult,
                             module_name: str) -> Optional[URMSymbol]:
        """Extract enum symbol."""
        name_node = None
        for child in enum_node.children:
            if child.type == "type_identifier":
                name_node = child
                break
        
        if not name_node:
            return None
        
        enum_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, enum_node)
        
        # Extract enumerators
        enumerators = []
        for child in enum_node.children:
            if child.type == "enumerator_list":
                for enum_child in child.children:
                    if enum_child.type == "enumerator":
                        for ec in enum_child.children:
                            if ec.type == "identifier":
                                enumerators.append(self._get_node_text(parse_result, ec))
        
        return URMSymbol(
            id=self._generate_symbol_id(enum_name, "cpp"),
            name=enum_name,
            qualified_name=f"{module_name}::{enum_name}",
            kind=SymbolKind.ENUM,
            language="cpp",
            location=location,
            stereotype="Enum",
            metadata={"enumerators": enumerators},
        )
    
    def _extract_function_symbol(self, func_node: Node, parse_result: ParseResult,
                                 module_name: str, parent_class: Optional[URMSymbol]) -> Optional[URMSymbol]:
        """Extract function symbol."""
        declarator = None
        for child in func_node.children:
            if child.type == "function_declarator":
                declarator = child
                break
        
        if not declarator:
            return None
        
        name_node = None
        for child in declarator.children:
            if child.type == "identifier":
                name_node = child
                break
        
        if not name_node:
            return None
        
        func_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, func_node)
        
        # Get parameters
        params = []
        for child in declarator.children:
            if child.type == "parameter_list":
                for param in child.children:
                    if child.type == "parameter_declaration":
                        param_name = ""
                        param_type = ""
                        for pc in param.children:
                            if pc.type == "identifier":
                                param_name = self._get_node_text(parse_result, pc)
                            elif pc.type in ("type_identifier", "generic_type", "reference_type", "pointer_type"):
                                param_type = self._get_node_text(parse_result, pc)
                        if param_name:
                            params.append({"name": param_name, "type": param_type})
        
        # Get return type
        return_type = ""
        for child in func_node.children:
            if child.type in ("type_identifier", "generic_type", "reference_type", "void_type"):
                if child.start_byte < declarator.start_byte:
                    return_type = self._get_node_text(parse_result, child)
        
        param_str = ", ".join([f"{p['type']} {p['name']}" for p in params])
        signature = f"{return_type} {func_name}({param_str})" if return_type else f"{func_name}({param_str})"
        
        # Check for inline, static, constexpr
        is_inline = False
        is_static = False
        is_constexpr = False
        for child in func_node.children:
            if child.type in ("inline", "static", "constexpr"):
                if child.type == "inline":
                    is_inline = True
                elif child.type == "static":
                    is_static = True
                elif child.type == "constexpr":
                    is_constexpr = True
        
        return URMSymbol(
            id=self._generate_symbol_id(func_name, "cpp"),
            name=func_name,
            qualified_name=f"{module_name}::{func_name}",
            kind=SymbolKind.FUNCTION,
            language="cpp",
            location=location,
            signature=signature,
            stereotype="Function",
            is_static=is_static,
            metadata={
                "parameters": params,
                "return_type": return_type,
                "is_inline": is_inline,
                "is_constexpr": is_constexpr,
            },
        )
    
    def _extract_typedef_symbol(self, typedef_node: Node, parse_result: ParseResult,
                                module_name: str) -> Optional[URMSymbol]:
        """Extract typedef/using symbol."""
        name_node = None
        for child in typedef_node.children:
            if child.type == "type_identifier":
                name_node = child
                break
        
        if not name_node:
            return None
        
        type_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, typedef_node)
        
        # Get aliased type
        aliased_type = ""
        for child in typedef_node.children:
            if child.type in ("type_identifier", "generic_type", "reference_type", "pointer_type", "function_type"):
                if child != name_node:
                    aliased_type = self._get_node_text(parse_result, child)
        
        return URMSymbol(
            id=self._generate_symbol_id(type_name, "cpp"),
            name=type_name,
            qualified_name=f"{module_name}::{type_name}",
            kind=SymbolKind.TYPE_ALIAS,
            language="cpp",
            location=location,
            signature=aliased_type,
            stereotype="TypeAlias",
        )
    
    def _extract_using_symbol(self, using_node: Node, parse_result: ParseResult,
                              module_name: str) -> Optional[URMSymbol]:
        """Extract using declaration."""
        name_node = None
        for child in using_node.children:
            if child.type == "identifier":
                name_node = child
                break
        
        if not name_node:
            return None
        
        using_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, using_node)
        
        return URMSymbol(
            id=self._generate_symbol_id(using_name, "cpp"),
            name=using_name,
            qualified_name=f"{module_name}::{using_name}",
            kind=SymbolKind.TYPE_ALIAS,
            language="cpp",
            location=location,
            stereotype="UsingAlias",
        )
    
    def extract_relationships(self, parse_result: ParseResult,
                              symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract relationships from C++ file."""
        relationships = []
        
        symbol_by_name = {s.name: s for s in symbols}
        symbol_by_qname = {s.qualified_name: s for s in symbols}
        
        # Class inheritance
        for symbol in symbols:
            if symbol.kind in (SymbolKind.CLASS, SymbolKind.STRUCT):
                base_classes = symbol.metadata.get("base_classes", [])
                for base in base_classes:
                    relationships.append(URMRelationship(
                        source_id=symbol.id,
                        target_id=base,
                        relationship_type=RelationshipType.EXTENDS,
                        language="cpp",
                    ))
        
        return relationships
    
    def extract_endpoints(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMEndpoint]:
        """Extract endpoints (not typical in C++ but possible with frameworks)."""
        endpoints = []
        
        # Check for framework-specific patterns (Crow, Pistache, Oat++, etc.)
        for symbol in symbols:
            if "handler" in symbol.name.lower() or "controller" in symbol.name.lower():
                endpoints.append(URMEndpoint(
                    route=f"/{symbol.name.lower()}",
                    http_method="GET",
                    handler_symbol_id=symbol.id,
                    framework="Crow / Pistache / Oat++ / Boost.Beast",
                    location=symbol.location,
                ))
        
        return endpoints
    
    def extract_configuration(self, parse_result: ParseResult) -> List[URMConfiguration]:
        """Extract configuration from CMakeLists.txt, conanfile, etc."""
        configs = []
        path = Path(parse_result.file_path)
        
        config_files = {
            "CMakeLists.txt": "cmake",
            "conanfile.txt": "conan",
            "conanfile.py": "conan",
            "vcpkg.json": "vcpkg",
            "meson.build": "meson",
            "Makefile": "make",
        }
        
        if path.name in config_files:
            config_type = config_files[path.name]
            
            if path.name == "CMakeLists.txt":
                lines = parse_result.source_code.splitlines()
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if line.startswith("project(") or line.startswith("cmake_minimum_required("):
                            configs.append(URMConfiguration(
                                file_path=parse_result.file_path,
                                config_type="cmake",
                                key=line.split("(")[0],
                                value=line,
                                location=SourceLocation(
                                    file_path=parse_result.file_path,
                                    start_line=i + 1, start_column=1,
                                    end_line=i + 1, end_column=len(line) + 1,
                                ),
                            ))
                        elif "find_package" in line or "add_subdirectory" in line:
                            configs.append(URMConfiguration(
                                file_path=parse_result.file_path,
                                config_type="cmake",
                                key="dependency",
                                value=line,
                                location=SourceLocation(
                                    file_path=parse_result.file_path,
                                    start_line=i + 1, start_column=1,
                                    end_line=i + 1, end_column=len(line) + 1,
                                ),
                            ))
        
        return configs
    
    def extract_frameworks(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMFramework]:
        """Detect C++ frameworks."""
        frameworks = []
        content = parse_result.source_code
        path = Path(parse_result.file_path)
        
        if path.name in ("CMakeLists.txt", "conanfile.txt", "conanfile.py", "vcpkg.json"):
            framework_patterns = {
                "Boost": "Boost",
                "Qt": "Qt",
                "OpenCV": "OpenCV",
                "Eigen": "Eigen",
                "fmt": "fmt",
                "spdlog": "spdlog",
                "nlohmann_json": "nlohmann/json",
                "catch2": "Catch2",
                "gtest": "GoogleTest",
                "gmock": "GoogleMock",
                "doctest": "doctest",
                "benchmark": "Google Benchmark",
                "tbb": "Intel TBB",
                "opencv": "OpenCV",
                "protobuf": "Protocol Buffers",
                "grpc": "gRPC",
                "cpr": "cpr",
                "curl": "libcurl",
                "openssl": "OpenSSL",
                "sqlite": "SQLite",
                "pqxx": "libpqxx",
                "oci": "Oracle OCI",
                "mongocxx": "MongoDB C++",
                "redis": "Redis++",
                "zmq": "ZeroMQ",
                "nanomsg": "nanomsg",
                "capnp": "Cap'n Proto",
                "flatbuffers": "FlatBuffers",
                "msgpack": "MessagePack",
                "yaml-cpp": "yaml-cpp",
                "tinyxml2": "TinyXML2",
                "pugixml": "pugixml",
                "rapidjson": "RapidJSON",
                "simdjson": "simdjson",
            }
            
            for pattern, framework in framework_patterns.items():
                if pattern.lower() in content.lower():
                    frameworks.append(URMFramework(
                        name=framework,
                        language="cpp",
                        evidence_files=[parse_result.file_path],
                    ))
        
        # Standard library features
        if "<thread>" in content or "<mutex>" in content or "<atomic>" in content:
            frameworks.append(URMFramework(
                name="C++ Threading", language="cpp", evidence_files=[parse_result.file_path],
            ))
        if "<coroutine>" in content or "co_await" in content:
            frameworks.append(URMFramework(
                name="C++ Coroutines", language="cpp", evidence_files=[parse_result.file_path],
            ))
        if "<concepts>" in content or "concept " in content:
            frameworks.append(URMFramework(
                name="C++ Concepts", language="cpp", evidence_files=[parse_result.file_path],
            ))
        if "<ranges>" in content or "std::ranges" in content:
            frameworks.append(URMFramework(
                name="C++ Ranges", language="cpp", evidence_files=[parse_result.file_path],
            ))
        if "<format>" in content or "std::format" in content:
            frameworks.append(URMFramework(
                name="C++ Format", language="cpp", evidence_files=[parse_result.file_path],
            ))
        
        return frameworks


