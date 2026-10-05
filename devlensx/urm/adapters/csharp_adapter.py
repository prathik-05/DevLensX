"""
DevLensX C# Language Adapter
Translates Tree-sitter C# CST to Universal Repository Model.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from tree_sitter import Node

from devlensx.urm.adapters.base import (
    BaseLanguageAdapter, SupportedLanguage, SymbolKind, RelationshipType,
    URMSymbol, URMRelationship, URMEndpoint, URMConfiguration, URMFramework,
    SourceLocation, ParseResult
)


class CSharpLanguageAdapter(BaseLanguageAdapter):
    """C# language adapter using Tree-sitter."""
    
    def __init__(self):
        super().__init__(SupportedLanguage.CSHARP)
    
    def get_file_extensions(self) -> tuple:
        return (".cs",)
        super().__init__(SupportedLanguage.CSHARP)
        
        # C# node types
        self.CLASS_TYPES = {"class_declaration", "record_declaration", "struct_declaration"}
        self.INTERFACE_TYPES = {"interface_declaration"}
        self.ENUM_TYPES = {"enum_declaration"}
        self.DELEGATE_TYPES = {"delegate_declaration"}
        self.METHOD_TYPES = {"method_declaration", "constructor_declaration", "destructor_declaration",
                            "property_declaration", "event_declaration", "operator_declaration"}
        self.FIELD_TYPES = {"field_declaration", "constant_declaration"}
        self.PROPERTY_TYPES = {"property_declaration", "indexer_declaration"}
        self.NAMESPACE_TYPES = {"namespace_declaration", "file_scoped_namespace_declaration"}
        self.USING_TYPES = {"using_directive", "using_alias_directive"}
        self.ATTRIBUTE_TYPES = {"attribute"}
    
    def extract_symbols(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Extract symbols from C# file."""
        symbols = []
        root = parse_result.root_node
        if not root:
            return symbols
        
        namespace = self._extract_namespace(root, parse_result)
        module_name = namespace or self._get_module_name(parse_result)
        
        # Extract using directives
        usings = self._extract_usings(root, parse_result)
        
        # Classes, records, structs
        for class_node in self._find_nodes_by_types(root, self.CLASS_TYPES):
            class_symbols = self._extract_class_symbols(class_node, parse_result, module_name)
            symbols.extend(class_symbols)
        
        # Interfaces
        for interface_node in self._find_nodes_by_types(root, self.INTERFACE_TYPES):
            interface_symbol = self._extract_interface_symbol(interface_node, parse_result, module_name)
            if interface_symbol:
                symbols.append(interface_symbol)
        
        # Enums
        for enum_node in self._find_nodes_by_types(root, self.ENUM_TYPES):
            enum_symbol = self._extract_enum_symbol(enum_node, parse_result, module_name)
            if enum_symbol:
                symbols.append(enum_symbol)
        
        # Delegates
        for delegate_node in self._find_nodes_by_types(root, self.DELEGATE_TYPES):
            delegate_symbol = self._extract_delegate_symbol(delegate_node, parse_result, module_name)
            if delegate_symbol:
                symbols.append(delegate_symbol)
        
        return symbols
    
    def _extract_namespace(self, root: Node, parse_result: ParseResult) -> str:
        """Extract namespace declaration."""
        for child in root.children:
            if child.type in ("namespace_declaration", "file_scoped_namespace_declaration"):
                for c in child.children:
                    if c.type in ("qualified_name", "identifier"):
                        return self._get_node_text(parse_result, c)
        return ""
    
    def _get_module_name(self, parse_result: ParseResult) -> str:
        """Get module name from file path."""
        path = Path(parse_result.file_path)
        return path.stem
    
    def _extract_usings(self, root: Node, parse_result: ParseResult) -> List[str]:
        """Extract using directives."""
        usings = []
        for using_node in self._find_nodes_by_types(root, self.USING_TYPES):
            for child in using_node.children:
                if child.type in ("qualified_name", "identifier"):
                    usings.append(self._get_node_text(parse_result, child))
        return usings
    
    def _extract_class_symbols(self, class_node: Node, parse_result: ParseResult,
                               module_name: str) -> List[URMSymbol]:
        """Extract class/record/struct and its members."""
        symbols = []
        
        name_node = self._find_child_by_type(class_node, "identifier")
        if not name_node:
            return symbols
        
        class_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, class_node)
        
        # Get attributes
        attributes = self._extract_attributes(class_node, parse_result)
        
        # Get base types
        base_types = []
        for child in class_node.children:
            if child.type == "base_list":
                for c in child.children:
                    if c.type in ("type_identifier", "generic_name"):
                        base_types.append(self._get_node_text(parse_result, c))
        
        # Get type parameters
        type_params = []
        for child in class_node.children:
            if child.type == "type_parameter_list":
                for c in child.children:
                    if c.type == "type_parameter":
                        for cc in c.children:
                            if cc.type == "identifier":
                                type_params.append(self._get_node_text(parse_result, cc))
        
        # Determine kind and stereotype
        node_type = class_node.type
        if node_type == "record_declaration":
            kind = SymbolKind.STRUCT
            base_stereotype = "Record"
        elif node_type == "struct_declaration":
            kind = SymbolKind.STRUCT
            base_stereotype = "Struct"
        else:
            kind = SymbolKind.CLASS
            base_stereotype = "Class"
        
        stereotype = self._classify_csharp_class(class_name, attributes, base_types, base_stereotype)
        
        class_symbol = URMSymbol(
            id=self._generate_symbol_id(class_name, "cs"),
            name=class_name,
            qualified_name=f"{module_name}.{class_name}",
            kind=kind,
            language="csharp",
            location=location,
            stereotype=stereotype,
            attributes=attributes,
            generics=type_params,
            metadata={
                "base_types": base_types,
                "is_abstract": "abstract" in self._extract_modifiers(class_node),
                "is_sealed": "sealed" in self._extract_modifiers(class_node),
                "is_partial": "partial" in self._extract_modifiers(class_node),
            },
        )
        symbols.append(class_symbol)
        
        # Extract members
        body_node = self._find_child_by_type(class_node, "declaration_list")
        if body_node:
            for member_node in body_node.children:
                member_symbols = self._extract_class_member(member_node, parse_result, class_symbol, module_name)
                symbols.extend(member_symbols)
        
        return symbols
    
    def _classify_csharp_class(self, class_name: str, attributes: List[str], 
                               base_types: List[str], base_stereotype: str) -> str:
        """Classify C# class based on attributes, base types, and naming."""
        # ASP.NET Core / .NET attributes
        attr_map = {
            "Controller": "Controller",
            "ControllerBase": "Controller",
            "ApiController": "Controller",
            "Service": "Service",
            "Repository": "Repository",
            "Entity": "Entity",
            "DbContext": "DbContext",
            "Configuration": "Configuration",
            "Options": "Configuration",
            "Middleware": "Middleware",
            "Filter": "Filter",
            "Attribute": "Attribute",
            "Dto": "DTO",
            "ViewModel": "ViewModel",
            "Command": "Command",
            "Query": "Query",
            "Handler": "Handler",
            "Validator": "Validator",
            "Mapper": "Mapper",
        }
        
        for attr in attributes:
            for key, value in attr_map.items():
                if key in attr:
                    return value
        
        # Check base types
        for base in base_types:
            base_lower = base.lower()
            if "controller" in base_lower:
                return "Controller"
            elif "service" in base_lower:
                return "Service"
            elif "repository" in base_lower or "repo" in base_lower:
                return "Repository"
            elif "context" in base_lower or "dbcontext" in base_lower:
                return "DbContext"
            elif "entity" in base_lower or "model" in base_lower:
                return "Entity"
        
        # Naming conventions
        name_lower = class_name.lower()
        if name_lower.endswith("controller"):
            return "Controller"
        elif name_lower.endswith("service"):
            return "Service"
        elif name_lower.endswith("repository") or name_lower.endswith("repo"):
            return "Repository"
        elif name_lower.endswith("handler"):
            return "Handler"
        elif name_lower.endswith("validator"):
            return "Validator"
        elif name_lower.endswith("mapper"):
            return "Mapper"
        elif name_lower.endswith("dto") or name_lower.endswith("viewmodel"):
            return "DTO"
        elif name_lower.endswith("entity") or name_lower.endswith("model"):
            return "Entity"
        elif name_lower.endswith("context") or name_lower.endswith("dbcontext"):
            return "DbContext"
        elif name_lower.endswith("config") or name_lower.endswith("settings"):
            return "Configuration"
        elif name_lower.endswith("middleware"):
            return "Middleware"
        elif name_lower.endswith("attribute"):
            return "Attribute"
        elif name_lower.endswith("exception") or name_lower.endswith("error"):
            return "Exception"
        elif name_lower.endswith("test"):
            return "Test"
        
        return base_stereotype
    
    def _extract_attributes(self, node: Node, parse_result: ParseResult) -> List[str]:
        """Extract C# attributes."""
        attributes = []
        for child in node.children:
            if child.type == "attribute_list":
                for attr in child.children:
                    if attr.type == "attribute":
                        for c in attr.children:
                            if c.type == "identifier":
                                attributes.append(self._get_node_text(parse_result, c))
        return attributes
    
    def _extract_modifiers(self, node: Node) -> List[str]:
        """Extract C# modifiers."""
        modifiers = []
        for child in node.children:
            if child.type == "modifier":
                modifiers.append(self._get_node_text_from_source(child))
        return modifiers
    
    def _extract_interface_symbol(self, interface_node: Node, parse_result: ParseResult,
                                  module_name: str) -> Optional[URMSymbol]:
        """Extract interface symbol."""
        name_node = self._find_child_by_type(interface_node, "identifier")
        if not name_node:
            return None
        
        interface_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, interface_node)
        
        return URMSymbol(
            id=self._generate_symbol_id(interface_name, "cs"),
            name=interface_name,
            qualified_name=f"{module_name}.{interface_name}",
            kind=SymbolKind.INTERFACE,
            language="csharp",
            location=location,
            stereotype="Interface",
            attributes=self._extract_attributes(interface_node, parse_result),
        )
    
    def _extract_enum_symbol(self, enum_node: Node, parse_result: ParseResult,
                             module_name: str) -> Optional[URMSymbol]:
        """Extract enum symbol."""
        name_node = self._find_child_by_type(enum_node, "identifier")
        if not name_node:
            return None
        
        enum_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, enum_node)
        
        # Extract enum members
        members = []
        for child in enum_node.children:
            if child.type == "enum_member_declaration":
                for c in child.children:
                    if c.type == "identifier":
                        members.append(self._get_node_text(parse_result, c))
        
        return URMSymbol(
            id=self._generate_symbol_id(enum_name, "cs"),
            name=enum_name,
            qualified_name=f"{module_name}.{enum_name}",
            kind=SymbolKind.ENUM,
            language="csharp",
            location=location,
            stereotype="Enum",
            metadata={"members": members},
        )
    
    def _extract_delegate_symbol(self, delegate_node: Node, parse_result: ParseResult,
                                 module_name: str) -> Optional[URMSymbol]:
        """Extract delegate symbol."""
        name_node = self._find_child_by_type(delegate_node, "identifier")
        if not name_node:
            return None
        
        delegate_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, delegate_node)
        
        return URMSymbol(
            id=self._generate_symbol_id(delegate_name, "cs"),
            name=delegate_name,
            qualified_name=f"{module_name}.{delegate_name}",
            kind=SymbolKind.TYPE_ALIAS,
            language="csharp",
            location=location,
            stereotype="Delegate",
        )
    
    def _extract_class_member(self, member_node: Node, parse_result: ParseResult,
                              parent_class: URMSymbol, module_name: str) -> List[URMSymbol]:
        """Extract class member (method, property, field, event)."""
        symbols = []
        location = self._create_location(parse_result, member_node)
        attributes = self._extract_attributes(member_node, parse_result)
        
        if member_node.type in ("method_declaration", "constructor_declaration", "destructor_declaration"):
            name_node = self._find_child_by_type(member_node, "identifier")
            if not name_node:
                return symbols
            
            member_name = self._get_node_text(parse_result, name_node)
            
            # Get parameters
            params = []
            for child in member_node.children:
                if child.type == "parameter_list":
                    for param in child.children:
                        if child.type == "parameter":
                            param_name = ""
                            param_type = ""
                            for pc in param.children:
                                if pc.type == "identifier":
                                    param_name = self._get_node_text(parse_result, pc)
                                elif pc.type in ("type_identifier", "generic_name", "array_type"):
                                    param_type = self._get_node_text(parse_result, pc)
                            if param_name:
                                params.append({"name": param_name, "type": param_type})
            
            # Get return type
            return_type = ""
            for child in member_node.children:
                if child.type in ("type_identifier", "generic_name", "void_keyword"):
                    return_type = self._get_node_text(parse_result, child)
            
            param_str = ", ".join([f"{p['name']} {p['type']}" for p in params])
            signature = f"{member_name}({param_str})"
            if return_type:
                signature = f"{return_type} {signature}"
            
            is_constructor = member_node.type == "constructor_declaration"
            is_destructor = member_node.type == "destructor_declaration"
            kind = SymbolKind.CONSTRUCTOR if is_constructor else SymbolKind.METHOD
            
            stereotype = "Constructor" if is_constructor else ("Destructor" if is_destructor else "Method")
            
            # Check for HTTP attributes
            for attr in attributes:
                if any(kw in attr for kw in ("HttpGet", "HttpPost", "HttpPut", "HttpDelete", "HttpPatch", "Route")):
                    stereotype = "Endpoint"
                    break
            
            qualified_name = f"{parent_class.qualified_name}.{member_name}"
            
            symbols.append(URMSymbol(
                id=self._generate_symbol_id(f"{parent_class.name}_{member_name}", "cs"),
                name=member_name,
                qualified_name=qualified_name,
                kind=kind,
                language="csharp",
                location=location,
                signature=signature,
                stereotype=stereotype,
                attributes=attributes,
                metadata={
                    "parent_class": parent_class.id,
                    "parameters": params,
                    "return_type": return_type,
                },
            ))
        
        elif member_node.type in ("property_declaration", "indexer_declaration"):
            name_node = self._find_child_by_type(member_node, "identifier")
            if name_node:
                prop_name = self._get_node_text(parse_result, name_node)
                
                # Get property type
                prop_type = ""
                for child in member_node.children:
                    if child.type in ("type_identifier", "generic_name", "array_type"):
                        prop_type = self._get_node_text(parse_result, child)
            
                symbols.append(URMSymbol(
                    id=self._generate_symbol_id(f"{parent_class.name}_{prop_name}", "cs"),
                    name=prop_name,
                    qualified_name=f"{parent_class.qualified_name}.{prop_name}",
                    kind=SymbolKind.PROPERTY,
                    language="csharp",
                    location=location,
                    signature=prop_type,
                    stereotype="Property",
                    attributes=attributes,
                    metadata={"parent_class": parent_class.id, "property_type": prop_type},
                ))
        
        elif member_node.type == "field_declaration":
            for child in member_node.children:
                if child.type == "variable_declarator":
                    name_node = self._find_child_by_type(child, "identifier")
                    if name_node:
                        field_name = self._get_node_text(parse_result, name_node)
                        
                        # Get field type
                        field_type = ""
                        for c in member_node.children:
                            if c.type in ("type_identifier", "generic_name", "array_type"):
                                field_type = self._get_node_text(parse_result, c)
                        
                        symbols.append(URMSymbol(
                            id=self._generate_symbol_id(f"{parent_class.name}_{field_name}", "cs"),
                            name=field_name,
                            qualified_name=f"{parent_class.qualified_name}.{field_name}",
                            kind=SymbolKind.FIELD,
                            language="csharp",
                            location=location,
                            signature=field_type,
                            stereotype="Field",
                            attributes=attributes,
                            metadata={"parent_class": parent_class.id, "field_type": field_type},
                        ))
        
        return symbols
    
    def extract_relationships(self, parse_result: ParseResult,
                              symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract relationships from C# file."""
        relationships = []
        root = parse_result.root_node
        if not root:
            return relationships
        
        symbol_by_name = {s.name: s for s in symbols}
        symbol_by_qname = {s.qualified_name: s for s in symbols}
        
        # Class inheritance
        for symbol in symbols:
            if symbol.kind in (SymbolKind.CLASS, SymbolKind.STRUCT):
                class_node = self._find_class_node(root, symbol.name)
                if class_node:
                    base_types = symbol.metadata.get("base_types", [])
                    for base in base_types:
                        relationships.append(URMRelationship(
                            source_id=symbol.id,
                            target_id=base,
                            relationship_type=RelationshipType.EXTENDS if base in symbol_by_name else RelationshipType.IMPLEMENTS,
                            language="csharp",
                        ))
        
        return relationships
    
    def _find_class_node(self, root: Node, class_name: str) -> Optional[Node]:
        """Find class node by name."""
        for node in self._find_nodes_by_types(root, self.CLASS_TYPES):
            name_node = self._find_child_by_type(node, "identifier")
            if name_node and self._get_node_text_from_source(name_node) == class_name:
                return node
        return None
    
    def extract_endpoints(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMEndpoint]:
        """Extract API endpoints from controller methods."""
        endpoints = []
        
        for symbol in symbols:
            if symbol.stereotype == "Endpoint":
                method = "GET"
                for attr in symbol.attributes:
                    if "HttpGet" in attr:
                        method = "GET"
                    elif "HttpPost" in attr:
                        method = "POST"
                    elif "HttpPut" in attr:
                        method = "PUT"
                    elif "HttpDelete" in attr:
                        method = "DELETE"
                    elif "HttpPatch" in attr:
                        method = "PATCH"
                
                route = f"/{symbol.metadata.get('parent_class', '').replace('Controller', '').lower()}/{symbol.name.lower()}"
                
                endpoints.append(URMEndpoint(
                    route=route,
                    http_method=method,
                    handler_symbol_id=symbol.id,
                    framework="ASP.NET Core",
                    location=symbol.location,
                ))
        
        return endpoints
    
    def extract_configuration(self, parse_result: ParseResult) -> List[URMConfiguration]:
        """Extract configuration from C# config files."""
        configs = []
        path = Path(parse_result.file_path)
        
        config_files = {
            "appsettings.json": "json",
            "appsettings.Development.json": "json",
            "appsettings.Production.json": "json",
            "web.config": "xml",
            "packages.config": "xml",
            "Directory.Build.props": "xml",
            "global.json": "json",
        }
        
        if path.name in config_files:
            config_type = config_files[path.name]
            
            if path.name.endswith(".json"):
                try:
                    import json
                    data = json.loads(parse_result.source_code)
                    for key, value in self._flatten_dict(data).items():
                        configs.append(URMConfiguration(
                            file_path=parse_result.file_path,
                            config_type="json",
                            key=key,
                            value=value,
                            location=SourceLocation(
                                file_path=parse_result.file_path,
                                start_line=1, start_column=1,
                                end_line=1, end_column=1,
                            ),
                        ))
                except:
                    pass
        
        return configs
    
    def _flatten_dict(self, d: Dict, parent_key: str = "") -> Dict[str, Any]:
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key))
            else:
                items[new_key] = v
        return items
    
    def extract_frameworks(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMFramework]:
        """Detect C#/.NET frameworks."""
        frameworks = []
        content = parse_result.source_code
        path = Path(parse_result.file_path)
        
        if path.name in (".csproj", "packages.config", "Directory.Build.props"):
            framework_patterns = {
                "Microsoft.AspNetCore": "ASP.NET Core",
                "Microsoft.EntityFrameworkCore": "Entity Framework Core",
                "Microsoft.Extensions.DependencyInjection": "DI Container",
                "Microsoft.Extensions.Configuration": "Configuration",
                "Microsoft.Extensions.Logging": "Logging",
                "Microsoft.Extensions.Hosting": "Hosting",
                "AutoMapper": "AutoMapper",
                "MediatR": "MediatR",
                "FluentValidation": "FluentValidation",
                "Serilog": "Serilog",
                "NLog": "NLog",
                "Swashbuckle": "Swagger/OpenAPI",
                "NSwag": "NSwag",
                "xunit": "xUnit",
                "NUnit": "NUnit",
                "Moq": "Moq",
                "FluentAssertions": "FluentAssertions",
                "MassTransit": "MassTransit",
                "StackExchange.Redis": "Redis",
                "MongoDB.Driver": "MongoDB",
                "RabbitMQ.Client": "RabbitMQ",
                "Confluent.Kafka": "Kafka",
                "Grpc.AspNetCore": "gRPC",
                "protobuf-net": "Protobuf",
                "Newtonsoft.Json": "JSON.NET",
                "System.Text.Json": "System.Text.Json",
            }
            
            for pattern, framework in framework_patterns.items():
                if pattern in content:
                    frameworks.append(URMFramework(
                        name=framework,
                        language="csharp",
                        evidence_files=[parse_result.file_path],
                    ))
        
        # Check for ASP.NET Core patterns in code
        if "Microsoft.AspNetCore" in content or "ControllerBase" in content:
            frameworks.append(URMFramework(
                name="ASP.NET Core", language="csharp", evidence_files=[parse_result.file_path],
            ))
        if "EntityFrameworkCore" in content or "DbContext" in content:
            frameworks.append(URMFramework(
                name="Entity Framework Core", language="csharp", evidence_files=[parse_result.file_path],
            ))
        
        return frameworks


