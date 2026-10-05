"""
DevLensX TypeScript/JavaScript Language Adapter
Translates Tree-sitter TypeScript/JavaScript CST to Universal Repository Model.
"""

import re
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from tree_sitter import Node

from devlensx.urm.adapters.base import (
    BaseLanguageAdapter, SupportedLanguage, SymbolKind, RelationshipType,
    URMSymbol, URMRelationship, URMEndpoint, URMConfiguration, URMFramework,
    SourceLocation, ParseResult
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def _is_valid_identifier(name: str) -> bool:
    """Guards against garbage symbol names from CST mis-extraction."""
    return bool(name) and bool(_IDENTIFIER_RE.match(name))


class TypeScriptLanguageAdapter(BaseLanguageAdapter):
    """TypeScript/JavaScript language adapter using Tree-sitter."""
    
    def __init__(self):
        super().__init__(SupportedLanguage.TYPESCRIPT)
        
        # TypeScript/JavaScript node types
        self.CLASS_TYPES = {"class_declaration", "abstract_class_declaration"}
        self.INTERFACE_TYPES = {"interface_declaration"}
        self.TYPE_ALIAS_TYPES = {"type_alias_declaration"}
        self.ENUM_TYPES = {"enum_declaration"}
        self.FUNCTION_TYPES = {"function_declaration", "function_signature", "method_definition"}
        self.ARROW_FUNCTION_TYPES = {"arrow_function"}
        self.VARIABLE_TYPES = {"variable_declaration", "lexical_declaration", "const_declaration"}
        self.IMPORT_TYPES = {"import_statement", "import_specifier", "namespace_import"}
        self.EXPORT_TYPES = {"export_statement", "export_specifier"}
        self.DECORATOR_TYPES = {"decorator"}
        self.CALL_TYPES = {"call_expression"}
        self.CLASS_MEMBER_TYPES = {
            "method_definition", "field_definition", "property_signature", 
            "constructor", "getter", "setter", "accessor"
        }
    
    def get_file_extensions(self) -> tuple:
        return (".ts", ".tsx", ".js", ".jsx")
    
    def extract_symbols(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Extract symbols from TypeScript/JavaScript file."""
        symbols = []
        root = parse_result.root_node
        if not root:
            return symbols
        
        # Track imports for dependency resolution
        imports = self._extract_imports(root, parse_result)
        
        # Extract module/file level info
        module_name = self._get_module_name(parse_result)
        
        # Classes
        for class_node in self._find_nodes_by_types(root, self.CLASS_TYPES):
            class_symbols = self._extract_class_symbols(class_node, parse_result, module_name, imports)
            symbols.extend(class_symbols)
        
        # Interfaces
        for interface_node in self._find_nodes_by_types(root, self.INTERFACE_TYPES):
            interface_symbol = self._extract_interface_symbol(interface_node, parse_result, module_name)
            if interface_symbol:
                symbols.append(interface_symbol)
        
        # Type aliases
        for type_node in self._find_nodes_by_types(root, self.TYPE_ALIAS_TYPES):
            type_symbol = self._extract_type_alias_symbol(type_node, parse_result, module_name)
            if type_symbol:
                symbols.append(type_symbol)
        
        # Enums
        for enum_node in self._find_nodes_by_types(root, self.ENUM_TYPES):
            enum_symbol = self._extract_enum_symbol(enum_node, parse_result, module_name)
            if enum_symbol:
                symbols.append(enum_symbol)
        
        # Standalone functions
        for func_node in self._find_nodes_by_types(root, self.FUNCTION_TYPES):
            # Only if not inside a class
            parent = func_node.parent
            if parent and parent.type not in self.CLASS_TYPES | {"class_body"}:
                func_symbol = self._extract_function_symbol(func_node, parse_result, module_name, None)
                if func_symbol:
                    symbols.append(func_symbol)
        
        # Arrow functions assigned to variables
        for var_node in self._find_nodes_by_types(root, self.VARIABLE_TYPES):
            arrow_symbols = self._extract_arrow_function_symbols(var_node, parse_result, module_name, imports)
            symbols.extend(arrow_symbols)
        
        return symbols
    
    def _get_module_name(self, parse_result: ParseResult) -> str:
        """Get module name from file path."""
        path = Path(parse_result.file_path)
        return path.stem
    
    def _extract_imports(self, root: Node, parse_result: ParseResult) -> List[Dict[str, Any]]:
        """Extract import statements with details."""
        imports = []
        for import_node in self._find_nodes_by_types(root, self.IMPORT_TYPES):
            import_info = {"source": "", "specifiers": [], "default": None, "namespace": None}
            
            # Get source module
            for child in import_node.children:
                if child.type == "string":
                    import_info["source"] = self._get_node_text(parse_result, child).strip('"\'')
                elif child.type == "import_specifier":
                    name = self._get_node_text(parse_result, child)
                    import_info["specifiers"].append(name)
                elif child.type == "namespace_import":
                    name = self._get_node_text(parse_result, child)
                    import_info["namespace"] = name
                elif child.type == "identifier" and not import_info["default"]:
                    import_info["default"] = self._get_node_text(parse_result, child)
            
            imports.append(import_info)
        
        return imports
    
    def _extract_class_symbols(self, class_node: Node, parse_result: ParseResult,
                               module_name: str, imports: List[Dict]) -> List[URMSymbol]:
        """Extract class and its members."""
        symbols = []
        
        name_node = self._find_child_by_type(class_node, "identifier", "type_identifier")
        if not name_node:
            return symbols
        
        class_name = self._get_node_text(parse_result, name_node)
        if not _is_valid_identifier(class_name):
            return symbols
        location = self._create_location(parse_result, class_node)
        
        # Determine stereotype from decorators and name
        decorators = self._extract_decorators(class_node, parse_result)
        stereotype = self._classify_typecript_class(class_name, decorators)
        
        # Extends/implements
        extends = self._extract_extends(class_node, parse_result)
        implements = self._extract_implements(class_node, parse_result)
        
        class_symbol = URMSymbol(
            id=self._generate_symbol_id(class_name, "ts"),
            name=class_name,
            qualified_name=f"{module_name}.{class_name}",
            kind=SymbolKind.CLASS,
            language="typescript",
            location=location,
            stereotype=stereotype,
            annotations=decorators,
            generics=self._extract_generics(class_node, parse_result),
            metadata={
                "extends": extends,
                "implements": implements,
                "is_abstract": "abstract" in self._extract_modifiers(class_node),
                "file_imports": [imp.get("source", "") for imp in (imports or [])
                                 if isinstance(imp, dict) and imp.get("source")],
            },
        )
        symbols.append(class_symbol)
        
        # Extract class members
        body_node = self._find_child_by_type(class_node, "class_body")
        if body_node:
            for member_node in body_node.children:
                if member_node.type in self.CLASS_MEMBER_TYPES:
                    member_symbols = self._extract_class_member(member_node, parse_result, class_symbol, module_name)
                    symbols.extend(member_symbols)
        
        return symbols
    
    def _classify_typecript_class(self, class_name: str, decorators: List[str]) -> str:
        """Classify TypeScript class based on decorators and naming."""
        # Angular/NestJS decorators
        decorator_map = {
            "Component": "Component",
            "Directive": "Directive",
            "Pipe": "Pipe",
            "Injectable": "Service",
            "NgModule": "Module",
            "Controller": "Controller",
            "Get": "Endpoint",
            "Post": "Endpoint",
            "Put": "Endpoint",
            "Delete": "Endpoint",
            "Patch": "Endpoint",
            "Module": "Module",
            "Entity": "Entity",
        }
        
        for dec in decorators:
            if dec in decorator_map:
                return decorator_map[dec]
        
        # Naming conventions
        name_lower = class_name.lower()
        if "service" in name_lower:
            return "Service"
        elif "component" in name_lower:
            return "Component"
        elif "controller" in name_lower:
            return "Controller"
        elif "repository" in name_lower or "dao" in name_lower:
            return "Repository"
        elif "entity" in name_lower or "model" in name_lower:
            return "Entity"
        elif "provider" in name_lower or "context" in name_lower:
            return "Provider"
        elif "hook" in name_lower or name_lower.startswith("use"):
            return "Hook"
        elif "util" in name_lower or "helper" in name_lower:
            return "Utility"
        
        return "Class"
    
    def _extract_decorators(self, node: Node, parse_result: ParseResult) -> List[str]:
        """Extract decorators from a node."""
        decorators = []
        for child in node.children:
            if child.type == "decorator":
                # Get decorator name
                for c in child.children:
                    if c.type == "identifier":
                        decorators.append(self._get_node_text(parse_result, c))
                        break
                    elif c.type == "call_expression":
                        for cc in c.children:
                            if cc.type == "identifier":
                                decorators.append(self._get_node_text(parse_result, cc))
                                break
        return decorators
    
    def _extract_modifiers(self, node: Node) -> List[str]:
        """Extract modifiers from a node."""
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for mod in child.children:
                    modifiers.append(self._get_node_text_from_source(mod))
        return modifiers
    
    def _extract_generics(self, node: Node, parse_result: ParseResult) -> List[str]:
        """Extract generic type parameters."""
        generics = []
        for child in node.children:
            if child.type == "type_parameters":
                for c in child.children:
                    if c.type == "type_parameter":
                        for cc in c.children:
                            if cc.type == "identifier":
                                generics.append(self._get_node_text(parse_result, cc))
        return generics
    
    def _extract_extends(self, class_node: Node, parse_result: ParseResult) -> List[str]:
        """Extract extends clause."""
        extends = []
        for child in class_node.children:
            if child.type == "class_heritage":
                for c in child.children:
                    if c.type == "extends_clause":
                        for cc in c.children:
                            if cc.type in ("identifier", "type_reference"):
                                extends.append(self._get_node_text(parse_result, cc))
        return extends
    
    def _extract_implements(self, class_node: Node, parse_result: ParseResult) -> List[str]:
        """Extract implements clause."""
        implements = []
        for child in class_node.children:
            if child.type == "class_heritage":
                for c in child.children:
                    if c.type == "implements_clause":
                        for cc in c.children:
                            if cc.type in ("identifier", "type_reference"):
                                implements.append(self._get_node_text(parse_result, cc))
        return implements
    
    def _extract_class_member(self, member_node: Node, parse_result: ParseResult,
                              parent_class: URMSymbol, module_name: str) -> List[URMSymbol]:
        """Extract class member (method, field, property)."""
        symbols = []
        location = self._create_location(parse_result, member_node)
        decorators = self._extract_decorators(member_node, parse_result)
        
        if member_node.type == "method_definition":
            name_node = self._find_child_by_type(member_node, "property_identifier", "identifier")
            if name_node:
                method_name = self._get_node_text(parse_result, name_node)
                
                # Check if it's a getter/setter
                is_getter = "get" in self._extract_modifiers(member_node)
                is_setter = "set" in self._extract_modifiers(member_node)
                is_constructor = method_name == "constructor"
                
                kind = SymbolKind.CONSTRUCTOR if is_constructor else SymbolKind.METHOD
                stereotype = "Constructor" if is_constructor else "Method"
                
                # Check for route decorators
                for dec in decorators:
                    if dec in ("Get", "Post", "Put", "Delete", "Patch", "Route"):
                        stereotype = "Endpoint"
                        break
                
                # Get parameters and return type
                params = []
                return_type = ""
                
                for child in member_node.children:
                    if child.type == "formal_parameters":
                        for param in child.children:
                            if param.type in ("required_parameter", "optional_parameter",
                                              "rest_parameter"):
                                param_name = ""
                                param_type = ""
                                for pchild in param.children:
                                    if pchild.type in ("identifier", "property_identifier"):
                                        if not param_name:
                                            param_name = self._get_node_text(parse_result, pchild)
                                    elif pchild.type in ("type_annotation", "type"):
                                        param_type = self._get_node_text(parse_result, pchild).replace(":", "").strip()
                                if param.type == "rest_parameter" and param_name:
                                    param_name = "..." + param_name
                                params.append({"name": param_name, "type": param_type})
                    elif child.type == "type_annotation":
                        return_type = self._get_node_text(parse_result, child).replace(":", "").strip()
                
                param_str = ", ".join([f"{p['name']}: {p['type']}" for p in params])
                signature = f"{method_name}({param_str})" + (f": {return_type}" if return_type else "")
                
                method_symbol = URMSymbol(
                    id=self._generate_symbol_id(f"{parent_class.name}_{method_name}", "ts"),
                    name=method_name,
                    qualified_name=f"{parent_class.qualified_name}.{method_name}",
                    kind=kind,
                    language="typescript",
                    location=location,
                    stereotype=stereotype,
                    signature=signature,
                    annotations=decorators,
                    modifiers=self._extract_modifiers(member_node),
                    is_static="static" in self._extract_modifiers(member_node),
                    is_async="async" in self._extract_modifiers(member_node),
                    metadata={
                        "parent_class": parent_class.id,
                        "parameters": params,
                        "return_type": return_type,
                        "is_getter": is_getter,
                        "is_setter": is_setter,
                    },
                )
                symbols.append(method_symbol)
        
        elif member_node.type in ("field_definition", "property_signature"):
            name_node = self._find_child_by_type(member_node, "property_identifier", "identifier")
            if name_node:
                field_name = self._get_node_text(parse_result, name_node)
                field_type = ""
                
                for child in member_node.children:
                    if child.type == "type_annotation":
                        field_type = self._get_node_text(parse_result, child).replace(":", "").strip()
                
                field_symbol = URMSymbol(
                    id=self._generate_symbol_id(f"{parent_class.name}_{field_name}", "ts"),
                    name=field_name,
                    qualified_name=f"{parent_class.qualified_name}.{field_name}",
                    kind=SymbolKind.FIELD,
                    language="typescript",
                    location=location,
                    signature=field_type,
                    annotations=decorators,
                    modifiers=self._extract_modifiers(member_node),
                    is_static="static" in self._extract_modifiers(member_node),
                    metadata={"parent_class": parent_class.id, "field_type": field_type},
                )
                symbols.append(field_symbol)
        
        return symbols
    
    def _extract_interface_symbol(self, interface_node: Node, parse_result: ParseResult,
                                  module_name: str) -> Optional[URMSymbol]:
        """Extract interface symbol."""
        name_node = self._find_child_by_type(interface_node, "identifier", "type_identifier")
        if not name_node:
            return None
        
        interface_name = self._get_node_text(parse_result, name_node)
        if not _is_valid_identifier(interface_name):
            return None
        location = self._create_location(parse_result, interface_node)
        
        extends = []
        for child in interface_node.children:
            if child.type == "extends_clause":
                for c in child.children:
                    if c.type in ("identifier", "type_reference"):
                        extends.append(self._get_node_text(parse_result, c))
        
        return URMSymbol(
            id=self._generate_symbol_id(interface_name, "ts"),
            name=interface_name,
            qualified_name=f"{module_name}.{interface_name}",
            kind=SymbolKind.INTERFACE,
            language="typescript",
            location=location,
            stereotype="Interface",
            metadata={"extends": extends},
        )
    
    def _extract_type_alias_symbol(self, type_node: Node, parse_result: ParseResult,
                                   module_name: str) -> Optional[URMSymbol]:
        """Extract type alias symbol."""
        name_node = self._find_child_by_type(type_node, "identifier", "type_identifier")
        if not name_node:
            return None
        
        type_name = self._get_node_text(parse_result, name_node)
        if not _is_valid_identifier(type_name):
            return None
        location = self._create_location(parse_result, type_node)
        
        # Get the actual type
        actual_type = ""
        for child in type_node.children:
            if child.type in ("type", "type_annotation", "union_type", "intersection_type", 
                            "object_type", "array_type", "function_type"):
                actual_type = self._get_node_text(parse_result, child)
        
        return URMSymbol(
            id=self._generate_symbol_id(type_name, "ts"),
            name=type_name,
            qualified_name=f"{module_name}.{type_name}",
            kind=SymbolKind.TYPE_ALIAS,
            language="typescript",
            location=location,
            signature=actual_type,
            stereotype="TypeAlias",
        )
    
    def _extract_enum_symbol(self, enum_node: Node, parse_result: ParseResult,
                             module_name: str) -> Optional[URMSymbol]:
        """Extract enum symbol."""
        name_node = self._find_child_by_type(enum_node, "identifier", "type_identifier")
        if not name_node:
            return None
        
        enum_name = self._get_node_text(parse_result, name_node)
        if not _is_valid_identifier(enum_name):
            return None
        location = self._create_location(parse_result, enum_node)
        
        return URMSymbol(
            id=self._generate_symbol_id(enum_name, "ts"),
            name=enum_name,
            qualified_name=f"{module_name}.{enum_name}",
            kind=SymbolKind.ENUM,
            language="typescript",
            location=location,
            stereotype="Enum",
        )
    
    def _extract_function_symbol(self, func_node: Node, parse_result: ParseResult,
                                 module_name: str, parent_class: Optional[URMSymbol]) -> Optional[URMSymbol]:
        """Extract function symbol."""
        name_node = self._find_child_by_type(func_node, "identifier")
        if not name_node:
            return None
        
        func_name = self._get_node_text(parse_result, name_node)
        if not _is_valid_identifier(func_name):
            return None
        location = self._create_location(parse_result, func_node)
        
        # Get parameters and return type
        params = []
        return_type = ""
        
        for child in func_node.children:
            if child.type == "formal_parameters":
                for param in child.children:
                    if param.type == "required_parameter":
                        param_name = ""
                        param_type = ""
                        for pchild in param.children:
                            if pchild.type == "identifier":
                                param_name = self._get_node_text(parse_result, pchild)
                            elif pchild.type in ("type_annotation", "type"):
                                param_type = self._get_node_text(parse_result, pchild).replace(":", "").strip()
                        params.append({"name": param_name, "type": param_type})
            elif child.type == "type_annotation":
                return_type = self._get_node_text(parse_result, child).replace(":", "").strip()
        
        param_str = ", ".join([f"{p['name']}: {p['type']}" for p in params])
        signature = f"{func_name}({param_str})" + (f": {return_type}" if return_type else "")

        # Stereotype: Hook (use*), React Component (PascalCase in .tsx/.jsx), else Function
        is_hook = func_name.startswith("use")
        is_component = (
            not is_hook
            and len(func_name) > 1
            and func_name[0].isupper()
            and parse_result.file_path.lower().endswith((".tsx", ".jsx"))
        )
        stereotype = "Hook" if is_hook else ("Component" if is_component else "Function")
        
        return URMSymbol(
            id=self._generate_symbol_id(func_name, "ts"),
            name=func_name,
            qualified_name=f"{module_name}.{func_name}",
            kind=SymbolKind.FUNCTION,
            language="typescript",
            location=location,
            signature=signature,
            stereotype=stereotype,
            is_async="async" in self._extract_modifiers(func_node),
            metadata={"parameters": params, "return_type": return_type},
        )
    
    def _extract_arrow_function_symbols(self, var_node: Node, parse_result: ParseResult,
                                        module_name: str, imports: List[Dict]) -> List[URMSymbol]:
        """Extract arrow functions assigned to variables."""
        symbols = []
        
        for child in var_node.children:
            if child.type == "variable_declarator":
                name_node = self._find_child_by_type(child, "identifier")
                value_node = self._find_child_by_type(child, "arrow_function")
                
                if name_node and value_node:
                    func_name = self._get_node_text(parse_result, name_node)
                    if not _is_valid_identifier(func_name):
                        continue
                    location = self._create_location(parse_result, value_node)
                    
                    # Get parameters and return type from arrow function
                    params = []
                    return_type = ""
                    
                    for c in value_node.children:
                        if c.type == "formal_parameters":
                            for param in c.children:
                                if param.type == "required_parameter":
                                    param_name = ""
                                    param_type = ""
                                    for pchild in param.children:
                                        if pchild.type == "identifier":
                                            param_name = self._get_node_text(parse_result, pchild)
                                        elif pchild.type in ("type_annotation", "type"):
                                            param_type = self._get_node_text(parse_result, pchild).replace(":", "").strip()
                                    params.append({"name": param_name, "type": param_type})
                        elif c.type == "type_annotation":
                            return_type = self._get_node_text(parse_result, c).replace(":", "").strip()
                    
                    param_str = ", ".join([f"{p['name']}: {p['type']}" for p in params])
                    signature = f"{func_name} = ({param_str})" + (f" => {return_type}" if return_type else " =>")
                    
                    is_hook = func_name.startswith("use")
                    
                    symbols.append(URMSymbol(
                        id=self._generate_symbol_id(func_name, "ts"),
                        name=func_name,
                        qualified_name=f"{module_name}.{func_name}",
                        kind=SymbolKind.FUNCTION,
                        language="typescript",
                        location=location,
                        signature=signature,
                        stereotype="Hook" if is_hook else "Function",
                        metadata={"parameters": params, "return_type": return_type, "is_arrow": True},
                    ))
        
        return symbols
    
    def extract_relationships(self, parse_result: ParseResult,
                              symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract relationships from TypeScript/JavaScript file."""
        relationships = []
        root = parse_result.root_node
        if not root:
            return relationships
        
        symbol_by_qname = {s.qualified_name: s for s in symbols}
        symbol_by_name = {s.name: s for s in symbols}

        # File-level relative imports, computed once (metadata["imports"]
        # is never populated on symbols — read the file directly).
        # Includes `@/` path-alias imports (Next.js/tsconfig convention for
        # repo-root-relative) alongside `./` and `../` relative imports.
        _file_import_sources = []
        try:
            for imp in self._extract_imports(root, parse_result):
                src = imp.get("source", "") if isinstance(imp, dict) else ""
                if src.startswith(".") or src.startswith("@/"):
                    if src not in _file_import_sources:
                        _file_import_sources.append(src)
        except Exception:
            pass

        # Process class inheritance
        for symbol in symbols:
            if symbol.kind == SymbolKind.CLASS:
                class_node = self._find_class_node(root, symbol.name)
                if class_node:
                    extends = self._extract_extends(class_node, parse_result)
                    for ext in extends:
                        self._add_relationship(relationships, symbol, ext, 
                                             RelationshipType.EXTENDS, parse_result)
                    
                    implements = self._extract_implements(class_node, parse_result)
                    for impl in implements:
                        self._add_relationship(relationships, symbol, impl,
                                             RelationshipType.IMPLEMENTS, parse_result)
            
            # Import relationships (file-level, relative imports only —
            # external packages cannot resolve to repository symbols).
            # Emitted from top-level symbols to avoid method-level fan-out.
            if symbol.kind in (SymbolKind.CLASS, SymbolKind.FUNCTION) and not symbol.metadata.get("parent_class"):
                for imp in _file_import_sources:
                    relationships.append(URMRelationship(
                        source_id=symbol.id,
                        target_id=imp,
                        relationship_type=RelationshipType.IMPORTS,
                        language="typescript",
                    ))

        # Same-file CALLS relationships: caller -> callee via call_expression
        relationships.extend(self._extract_call_relationships(parse_result, symbols))

        return relationships

    def _extract_call_relationships(self, parse_result: ParseResult,
                                    symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract CALLS edges between symbols defined in the same file."""
        root = parse_result.root_node
        if not root:
            return []

        callables = {
            s.name: s for s in symbols
            if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD, SymbolKind.CONSTRUCTOR)
        }
        containers = [
            s for s in symbols
            if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD, SymbolKind.CLASS)
        ]

        def enclosing_symbol(node: Node) -> Optional[URMSymbol]:
            cur = node.parent
            while cur is not None:
                for s in containers:
                    sl = s.location
                    if (cur.start_point[0] + 1 >= sl.start_line
                            and cur.end_point[0] + 1 <= sl.end_line
                            and self._node_defines_name(cur, s.name)):
                        return s
                cur = cur.parent
            return None

        relationships = []
        seen = set()
        for call_node in self._find_nodes_by_types(root, {"call_expression"}):
            callee_node = call_node.child_by_field_name("function") or (
                call_node.children[0] if call_node.children else None
            )
            if callee_node is None:
                continue
            callee_text = ""
            if callee_node.type == "identifier":
                callee_text = self._get_node_text(parse_result, callee_node)
            elif callee_node.type in ("member_expression",):
                # take property segment for method calls
                prop = callee_node.child_by_field_name("property")
                if prop is not None:
                    callee_text = self._get_node_text(parse_result, prop)

            target = callables.get(callee_text)
            if target is None:
                continue

            caller = enclosing_symbol(call_node)
            if caller is None or caller.id == target.id:
                continue

            key = (caller.id, target.id)
            if key in seen:
                continue
            seen.add(key)

            relationships.append(URMRelationship(
                source_id=caller.id,
                target_id=target.id,
                relationship_type=RelationshipType.CALLS,
                language="typescript",
                location=self._create_location(parse_result, call_node),
            ))

        return relationships

    def _node_defines_name(self, node: Node, name: str) -> bool:
        """Check whether a node declares the given identifier name directly."""
        for child in node.children:
            if child.type == "identifier" and self._get_node_text_from_source(child) == name:
                return True
        return False
    
    def _find_class_node(self, root: Node, class_name: str) -> Optional[Node]:
        """Find class node by name."""
        for node in self._find_nodes_by_types(root, self.CLASS_TYPES):
            name_node = self._find_child_by_type(node, "identifier", "type_identifier")
            if name_node and self._get_node_text_from_source(name_node) == class_name:
                return node
        return None
    
    def _add_relationship(self, relationships: List[URMRelationship],
                         source: URMSymbol, target_name: str, rel_type: RelationshipType,
                         parse_result: ParseResult):
        """Add relationship."""
        relationships.append(URMRelationship(
            source_id=source.id,
            target_id=target_name,
            relationship_type=rel_type,
            language="typescript",
        ))
    
    def extract_endpoints(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMEndpoint]:
        """Extract API endpoints from decorators."""
        endpoints = []
        root = parse_result.root_node
        if not root:
            return endpoints
        
        # Framework route decorators
        route_decorators = {
            "Get": "GET", "Post": "POST", "Put": "PUT", 
            "Delete": "DELETE", "Patch": "PATCH", "Route": "GET",
            "Controller": "CONTROLLER",  # NestJS
        }
        
        # Also check for Express-style app.get/post
        for call_node in self._find_nodes_by_types(root, self.CALL_TYPES):
            # Check for express app.METHOD patterns
            pass
        
        # For now, use symbols with endpoint stereotype
        for symbol in symbols:
            if symbol.stereotype == "Endpoint":
                method = "GET"
                for ann in symbol.annotations:
                    if ann in route_decorators:
                        method = route_decorators[ann]
                        break
                
                # Try to extract path from decorator
                path = self._extract_decorator_path(symbol, parse_result)
                
                endpoints.append(URMEndpoint(
                    route=path or f"/{symbol.name.lower()}",
                    http_method=method,
                    handler_symbol_id=symbol.id,
                    framework="NestJS/Express",
                    location=symbol.location,
                ))
        
        return endpoints
    
    def _extract_decorator_path(self, symbol: URMSymbol, parse_result: ParseResult) -> Optional[str]:
        """Extract the route path from a decorator call, e.g. @Get('users/:id')."""
        import re as _re
        root = parse_result.root_node
        if not root:
            return None
        target = (symbol.name or "").lower()
        for dec in self._find_nodes_by_types(root, {"decorator"}):
            text = self._get_node_text(parse_result, dec)
            m = _re.search(r"@(\w+)\s*\(\s*['\"]([^'\"]+)['\"]", text)
            if not m:
                continue
            if m.group(1).lower() in ("get", "post", "put", "delete", "patch", "route", "all"):
                path = m.group(2).strip()
                if path:
                    return path if path.startswith("/") else "/" + path
        # Fallback: decorator attached near a same-named method
        _ = target
        return None
    
    def extract_configuration(self, parse_result: ParseResult) -> List[URMConfiguration]:
        """Extract configuration from package.json, tsconfig, etc."""
        configs = []
        path = Path(parse_result.file_path)
        
        config_files = {
            "package.json": "npm",
            "tsconfig.json": "typescript",
            "vite.config.ts": "vite",
            "next.config.js": "nextjs",
            "next.config.ts": "nextjs",
            "webpack.config.js": "webpack",
            ".env": "env",
            ".env.local": "env",
            ".env.example": "env",
        }
        
        if path.name in config_files:
            config_type = config_files[path.name]
            
            if path.name == "package.json":
                # Parse package.json
                import json
                try:
                    data = json.loads(parse_result.source_code)
                    for key, value in data.items():
                        configs.append(URMConfiguration(
                            file_path=parse_result.file_path,
                            config_type=config_type,
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
            elif path.name.endswith(".env"):
                # Parse .env files
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
                          "private", "credential", "auth", "secret"]
        return any(p in key.lower() for p in secret_patterns)
    
    def extract_frameworks(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMFramework]:
        """Detect TypeScript/JavaScript frameworks."""
        frameworks = []
        content = parse_result.source_code
        path = Path(parse_result.file_path)
        
        # Check package.json for dependencies
        if path.name == "package.json":
            import json
            try:
                data = json.loads(content)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                
                framework_map = {
                    "next": "Next.js",
                    "react": "React",
                    "vue": "Vue.js",
                    "@angular/core": "Angular",
                    "svelte": "Svelte",
                    "express": "Express",
                    "fastify": "Fastify",
                    "koa": "Koa",
                    "nest": "NestJS",
                    "adonis": "AdonisJS",
                    "remix": "Remix",
                    "astro": "Astro",
                    "nuxt": "Nuxt.js",
                    "gatsby": "Gatsby",
                }
                
                for dep, framework in framework_map.items():
                    if dep in deps:
                        frameworks.append(URMFramework(
                            name=framework,
                            language="typescript" if "typescript" in deps else "javascript",
                            version=deps.get(dep),
                            evidence_files=[parse_result.file_path],
                        ))
            except:
                pass
        
        # Check for framework-specific patterns in code
        if "createContext" in content or "useContext" in content:
            frameworks.append(URMFramework(
                name="React Context",
                language="typescript",
                evidence_files=[parse_result.file_path],
            ))
        
        return frameworks



