"""
DevLensX Rust Language Adapter
Translates Tree-sitter Rust CST to Universal Repository Model.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from tree_sitter import Node

from devlensx.urm.adapters.base import (
    BaseLanguageAdapter, SupportedLanguage, SymbolKind, RelationshipType,
    URMSymbol, URMRelationship, URMEndpoint, URMConfiguration, URMFramework,
    SourceLocation, ParseResult
)


class RustLanguageAdapter(BaseLanguageAdapter):
    """Rust language adapter using Tree-sitter."""
    
    def __init__(self):
        super().__init__(SupportedLanguage.RUST)
    
    def get_file_extensions(self) -> tuple:
        return (".rs",)
        super().__init__(SupportedLanguage.RUST)
        
        # Rust node types
        self.STRUCT_TYPES = {"struct_item"}
        self.ENUM_TYPES = {"enum_item"}
        self.TRAIT_TYPES = {"trait_item"}
        self.IMPL_TYPES = {"impl_item"}
        self.FUNCTION_TYPES = {"function_item"}
        self.CONST_TYPES = {"const_item", "static_item"}
        self.TYPE_ALIAS_TYPES = {"type_item"}
        self.MODULE_TYPES = {"mod_item"}
        self.USE_TYPES = {"use_declaration"}
        self.MACRO_TYPES = {"macro_invocation"}
    
    def extract_symbols(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Extract symbols from Rust file."""
        symbols = []
        root = parse_result.root_node
        if not root:
            return symbols
        
        module_name = self._get_module_name(parse_result)
        
        # Extract structs
        for struct_node in self._find_nodes_by_types(root, self.STRUCT_TYPES):
            struct_symbol = self._extract_struct_symbol(struct_node, parse_result, module_name)
            if struct_symbol:
                symbols.append(struct_symbol)
        
        # Extract enums
        for enum_node in self._find_nodes_by_types(root, self.ENUM_TYPES):
            enum_symbol = self._extract_enum_symbol(enum_node, parse_result, module_name)
            if enum_symbol:
                symbols.append(enum_symbol)
        
        # Extract traits
        for trait_node in self._find_nodes_by_types(root, self.TRAIT_TYPES):
            trait_symbol = self._extract_trait_symbol(trait_node, parse_result, module_name)
            if trait_symbol:
                symbols.append(trait_symbol)
        
        # Extract impl blocks
        for impl_node in self._find_nodes_by_types(root, self.IMPL_TYPES):
            impl_symbols = self._extract_impl_symbols(impl_node, parse_result, module_name)
            symbols.extend(impl_symbols)
        
        # Extract functions
        for func_node in self._find_nodes_by_types(root, self.FUNCTION_TYPES):
            func_symbol = self._extract_function_symbol(func_node, parse_result, module_name)
            if func_symbol:
                symbols.append(func_symbol)
        
        # Extract constants/statics
        for const_node in self._find_nodes_by_types(root, self.CONST_TYPES):
            const_symbol = self._extract_const_symbol(const_node, parse_result, module_name)
            if const_symbol:
                symbols.append(const_symbol)
        
        # Extract type aliases
        for type_node in self._find_nodes_by_types(root, self.TYPE_ALIAS_TYPES):
            type_symbol = self._extract_type_alias_symbol(type_node, parse_result, module_name)
            if type_symbol:
                symbols.append(type_symbol)
        
        return symbols
    
    def _get_module_name(self, parse_result: ParseResult) -> str:
        """Get module name from file path."""
        path = Path(parse_result.file_path)
        return path.stem
    
    def _extract_struct_symbol(self, struct_node: Node, parse_result: ParseResult,
                               module_name: str) -> Optional[URMSymbol]:
        """Extract struct symbol."""
        name_node = self._find_child_by_type(struct_node, "type_identifier")
        if not name_node:
            return None
        
        struct_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, struct_node)
        
        # Check for derives
        derives = []
        for child in struct_node.children:
            if child.type == "attribute":
                attr_text = self._get_node_text(parse_result, child)
                if "derive" in attr_text:
                    derives.append(attr_text)
        
        # Determine stereotype
        stereotype = self._classify_rust_struct(struct_name, derives)
        
        # Extract fields
        fields = []
        for child in struct_node.children:
            if child.type == "field_declaration_list":
                for field in child.children:
                    if field.type == "field_declaration":
                        field_name = ""
                        field_type = ""
                        for fc in field.children:
                            if fc.type == "field_identifier":
                                field_name = self._get_node_text(parse_result, fc)
                            elif fc.type in ("type_identifier", "generic_type", "reference_type"):
                                field_type = self._get_node_text(parse_result, fc)
                        if field_name:
                            fields.append({"name": field_name, "type": field_type})
        
        return URMSymbol(
            id=self._generate_symbol_id(struct_name, "rs"),
            name=struct_name,
            qualified_name=f"{module_name}::{struct_name}",
            kind=SymbolKind.STRUCT,
            language="rust",
            location=location,
            stereotype=stereotype,
            metadata={"derives": derives, "fields": fields},
        )
    
    def _classify_rust_struct(self, struct_name: str, derives: List[str]) -> str:
        """Classify Rust struct based on name and derives."""
        name_lower = struct_name.lower()
        
        # Check for common framework derives
        framework_derives = {
            "Serialize": "Model",
            "Deserialize": "Model",
            "Debug": "Model",
            "Clone": "Model",
            "Default": "Model",
            "sqlx::FromRow": "Entity",
            "diesel::Queryable": "Entity",
            "serde::Serialize": "Model",
            "serde::Deserialize": "Model",
        }
        
        for derive in derives:
            for key, value in framework_derives.items():
                if key in derive:
                    return value
        
        # Naming conventions
        if name_lower.endswith("request") or name_lower.endswith("response"):
            return "DTO"
        elif name_lower.endswith("config") or name_lower.endswith("settings"):
            return "Configuration"
        elif name_lower.endswith("error"):
            return "Error"
        elif "service" in name_lower:
            return "Service"
        elif "repository" in name_lower or "repo" in name_lower:
            return "Repository"
        elif "handler" in name_lower or "controller" in name_lower:
            return "Handler"
        elif "model" in name_lower or "entity" in name_lower:
            return "Model"
        
        return "Struct"
    
    def _extract_enum_symbol(self, enum_node: Node, parse_result: ParseResult,
                             module_name: str) -> Optional[URMSymbol]:
        """Extract enum symbol."""
        name_node = self._find_child_by_type(enum_node, "type_identifier")
        if not name_node:
            return None
        
        enum_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, enum_node)
        
        # Extract variants
        variants = []
        for child in enum_node.children:
            if child.type == "enum_variant_list":
                for variant in child.children:
                    if variant.type == "enum_variant":
                        for vc in variant.children:
                            if vc.type == "identifier":
                                variants.append(self._get_node_text(parse_result, vc))
        
        return URMSymbol(
            id=self._generate_symbol_id(enum_name, "rs"),
            name=enum_name,
            qualified_name=f"{module_name}::{enum_name}",
            kind=SymbolKind.ENUM,
            language="rust",
            location=location,
            stereotype="Enum",
            metadata={"variants": variants},
        )
    
    def _extract_trait_symbol(self, trait_node: Node, parse_result: ParseResult,
                              module_name: str) -> Optional[URMSymbol]:
        """Extract trait symbol."""
        name_node = self._find_child_by_type(trait_node, "type_identifier")
        if not name_node:
            return None
        
        trait_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, trait_node)
        
        return URMSymbol(
            id=self._generate_symbol_id(trait_name, "rs"),
            name=trait_name,
            qualified_name=f"{module_name}::{trait_name}",
            kind=SymbolKind.INTERFACE,
            language="rust",
            location=location,
            stereotype="Trait",
        )
    
    def _extract_impl_symbols(self, impl_node: Node, parse_result: ParseResult,
                              module_name: str) -> List[URMSymbol]:
        """Extract methods from impl block."""
        symbols = []
        
        # Get the type this impl is for
        impl_type = ""
        for child in impl_node.children:
            if child.type == "type_identifier":
                impl_type = self._get_node_text(parse_result, child)
                break
        
        # Extract methods
        for child in impl_node.children:
            if child.type == "declaration_list":
                for item in child.children:
                    if item.type == "function_item":
                        func_symbol = self._extract_function_symbol(item, parse_result, module_name, None)
                        if func_symbol:
                            func_symbol.metadata["impl_for"] = impl_type
                            func_symbol.qualified_name = f"{module_name}::{impl_type}::{func_symbol.name}"
                            symbols.append(func_symbol)
        
        return symbols
    
    def _extract_function_symbol(self, func_node: Node, parse_result: ParseResult,
                                 module_name: str, parent_type: Optional[URMSymbol]) -> Optional[URMSymbol]:
        """Extract function symbol."""
        name_node = self._find_child_by_type(func_node, "identifier")
        if not name_node:
            return None
        
        func_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, func_node)
        
        # Check for attributes
        attrs = []
        for child in func_node.children:
            if child.type == "attribute":
                attrs.append(self._get_node_text(parse_result, child))
        
        # Get parameters
        params = []
        for child in func_node.children:
            if child.type == "parameters":
                for param in child.children:
                    if param.type == "parameter":
                        param_name = ""
                        param_type = ""
                        for pc in param.children:
                            if pc.type == "identifier":
                                param_name = self._get_node_text(parse_result, pc)
                            elif pc.type in ("type_identifier", "generic_type", "reference_type"):
                                param_type = self._get_node_text(parse_result, pc)
                        if param_name:
                            params.append({"name": param_name, "type": param_type})
        
        # Get return type
        return_type = ""
        for child in func_node.children:
            if child.type == "return_type":
                return_type = self._get_node_text(parse_result, child).replace("->", "").strip()
        
        # Check for async
        is_async = False
        for child in func_node.children:
            if child.type == "async":
                is_async = True
        
        param_str = ", ".join([f"{p['name']}: {p['type']}" for p in params])
        signature = f"{func_name}({param_str})"
        if return_type:
            signature += f" -> {return_type}"
        
        # Determine stereotype
        stereotype = "Function"
        if func_name == "main":
            stereotype = "Main"
        elif func_name.startswith("test_"):
            stereotype = "Test"
        elif any("handler" in attr.lower() or "route" in attr.lower() or "get" in attr.lower() 
                or "post" in attr.lower() for attr in attrs):
            stereotype = "Handler"
        
        return URMSymbol(
            id=self._generate_symbol_id(func_name, "rs"),
            name=func_name,
            qualified_name=f"{module_name}::{func_name}",
            kind=SymbolKind.FUNCTION,
            language="rust",
            location=location,
            signature=signature,
            stereotype=stereotype,
            is_async=is_async,
            metadata={"attributes": attrs, "parameters": params, "return_type": return_type},
        )
    
    def _extract_const_symbol(self, const_node: Node, parse_result: ParseResult,
                              module_name: str) -> Optional[URMSymbol]:
        """Extract const/static symbol."""
        name_node = self._find_child_by_type(const_node, "identifier")
        if not name_node:
            return None
        
        const_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, const_node)
        
        is_static = const_node.type == "static_item"
        
        return URMSymbol(
            id=self._generate_symbol_id(const_name, "rs"),
            name=const_name,
            qualified_name=f"{module_name}::{const_name}",
            kind=SymbolKind.CONSTANT,
            language="rust",
            location=location,
            stereotype="Static" if is_static else "Constant",
        )
    
    def _extract_type_alias_symbol(self, type_node: Node, parse_result: ParseResult,
                                   module_name: str) -> Optional[URMSymbol]:
        """Extract type alias symbol."""
        name_node = self._find_child_by_type(type_node, "type_identifier")
        if not name_node:
            return None
        
        type_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, type_node)
        
        # Get aliased type
        aliased_type = ""
        for child in type_node.children:
            if child.type in ("type_identifier", "generic_type", "reference_type", "tuple_type"):
                aliased_type = self._get_node_text(parse_result, child)
        
        return URMSymbol(
            id=self._generate_symbol_id(type_name, "rs"),
            name=type_name,
            qualified_name=f"{module_name}::{type_name}",
            kind=SymbolKind.TYPE_ALIAS,
            language="rust",
            location=location,
            signature=aliased_type,
            stereotype="TypeAlias",
        )
    
    def extract_relationships(self, parse_result: ParseResult,
                              symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract relationships from Rust file."""
        relationships = []
        root = parse_result.root_node
        if not root:
            return relationships
        
        symbol_by_name = {s.name: s for s in symbols}
        
        # Trait implementations
        for impl_node in self._find_nodes_by_types(root, self.IMPL_TYPES):
            impl_for = ""
            trait_name = ""
            
            for child in impl_node.children:
                if child.type == "type_identifier":
                    impl_for = self._get_node_text(parse_result, child)
                elif child.type == "trait_identifier":
                    trait_name = self._get_node_text(parse_result, child)
            
            if impl_for and trait_name:
                relationships.append(URMRelationship(
                    source_id=impl_for,
                    target_id=trait_name,
                    relationship_type=RelationshipType.IMPLEMENTS,
                    language="rust",
                ))
        
        return relationships
    
    def extract_endpoints(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMEndpoint]:
        """Extract HTTP endpoints from Rust handlers."""
        endpoints = []
        
        # Check for actix-web, axum, warp, rocket handlers
        for symbol in symbols:
            if symbol.stereotype == "Handler":
                # Check attributes for route info
                route_path = f"/{symbol.name.lower()}"
                method = "GET"
                
                for attr in symbol.metadata.get("attributes", []):
                    if "get" in attr.lower():
                        method = "GET"
                    elif "post" in attr.lower():
                        method = "POST"
                    elif "put" in attr.lower():
                        method = "PUT"
                    elif "delete" in attr.lower():
                        method = "DELETE"
                
                endpoints.append(URMEndpoint(
                    route=route_path,
                    http_method=method,
                    handler_symbol_id=symbol.id,
                    framework="Actix-web / Axum / Warp / Rocket",
                    location=symbol.location,
                ))
        
        return endpoints
    
    def extract_configuration(self, parse_result: ParseResult) -> List[URMConfiguration]:
        """Extract configuration from Cargo.toml and .env files."""
        configs = []
        path = Path(parse_result.file_path)
        
        if path.name == "Cargo.toml":
            try:
                import toml
                data = toml.loads(parse_result.source_code)
                
                # Package info
                if "package" in data:
                    for key, value in data["package"].items():
                        configs.append(URMConfiguration(
                            file_path=parse_result.file_path,
                            config_type="cargo",
                            key=f"package.{key}",
                            value=value,
                            location=SourceLocation(
                                file_path=parse_result.file_path,
                                start_line=1, start_column=1,
                                end_line=1, end_column=1,
                            ),
                        ))
                
                # Dependencies
                for dep_section in ["dependencies", "dev-dependencies", "build-dependencies"]:
                    if dep_section in data:
                        for dep, value in data[dep_section].items():
                            dep_info = value if isinstance(value, str) else str(value)
                            configs.append(URMConfiguration(
                                file_path=parse_result.file_path,
                                config_type="cargo",
                                key=f"{dep_section}.{dep}",
                                value=dep_info,
                                location=SourceLocation(
                                    file_path=parse_result.file_path,
                                    start_line=1, start_column=1,
                                    end_line=1, end_column=1,
                                ),
                            ))
            except:
                pass
        
        elif path.name == ".env":
            lines = parse_result.source_code.splitlines()
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    configs.append(URMConfiguration(
                        file_path=parse_result.file_path,
                        config_type="env",
                        key=key.strip(),
                        value=value.strip(),
                        location=SourceLocation(
                            file_path=parse_result.file_path,
                            start_line=i + 1, start_column=1,
                            end_line=i + 1, end_column=len(line) + 1,
                        ),
                        is_secret=self._is_secret_key(key.strip()),
                    ))
        
        return configs
    
    def _is_secret_key(self, key: str) -> bool:
        secret_patterns = ["secret", "key", "token", "password", "api_key", "apikey",
                          "private", "credential", "auth", "database_url"]
        return any(p in key.lower() for p in secret_patterns)
    
    def extract_frameworks(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMFramework]:
        """Detect Rust frameworks."""
        frameworks = []
        content = parse_result.source_code
        path = Path(parse_result.file_path)
        
        if path.name == "Cargo.toml":
            framework_patterns = {
                "actix-web": "Actix-web",
                "axum": "Axum",
                "warp": "Warp",
                "rocket": "Rocket",
                "tide": "Tide",
                "hyper": "Hyper",
                "reqwest": "Reqwest",
                "tokio": "Tokio",
                "async-std": "async-std",
                "serde": "Serde",
                "sqlx": "SQLx",
                "diesel": "Diesel",
                "sea-orm": "SeaORM",
                "mongodb": "MongoDB Rust",
                "redis": "Redis",
                "lapin": "RabbitMQ",
                "rdkafka": "Kafka",
                "tower": "Tower",
                "tonic": "Tonic (gRPC)",
                "prost": "Prost (Protobuf)",
                "clap": "Clap",
                "structopt": "StructOpt",
                "anyhow": "Anyhow",
                "thiserror": "ThisError",
                "tracing": "Tracing",
                "log": "Log",
                "env_logger": "Env Logger",
            }
            
            for pattern, framework in framework_patterns.items():
                if pattern in content:
                    frameworks.append(URMFramework(
                        name=framework,
                        language="rust",
                        evidence_files=[parse_result.file_path],
                    ))
        
        return frameworks


