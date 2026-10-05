"""
DevLensX Java Language Adapter
Translates Tree-sitter Java CST to Universal Repository Model.
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


class JavaLanguageAdapter(BaseLanguageAdapter):
    """Java language adapter using Tree-sitter."""
    
    def __init__(self):
        super().__init__(SupportedLanguage.JAVA)
        
        # Java node types we care about
        self.CLASS_TYPES = {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}
        self.METHOD_TYPES = {"method_declaration", "constructor_declaration"}
        self.FIELD_TYPES = {"field_declaration"}
        self.IMPORT_TYPES = {"import_declaration"}
        self.ANNOTATION_TYPES = {"annotation", "marker_annotation", "normal_annotation"}
        self.PACKAGE_TYPE = "package_declaration"
    
    def get_file_extensions(self) -> tuple:
        return (".java",)
    
    def extract_symbols(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Extract symbols from Java file."""
        symbols = []
        root = parse_result.root_node
        if not root:
            return symbols
        
        # Get package name
        package_name = self._extract_package(root, parse_result)
        
        # Extract imports first
        imports = self._extract_imports(root, parse_result)
        
        # Extract classes/interfaces/enums/records
        for class_node in self._find_nodes_by_types(root, self.CLASS_TYPES):
            class_symbols = self._extract_class_symbols(class_node, parse_result, package_name, imports)
            symbols.extend(class_symbols)
        
        # Extract standalone methods (not in class) - rare in Java but possible in scripts
        for method_node in self._find_nodes_by_types(root, self.METHOD_TYPES):
            # Only if not already captured as part of a class
            parent = method_node.parent
            if parent and parent.type not in self.CLASS_TYPES:
                method_symbol = self._extract_method_symbol(method_node, parse_result, package_name, None)
                if method_symbol:
                    symbols.append(method_symbol)
        
        return symbols
    
    def _extract_package(self, root: Node, parse_result: ParseResult) -> str:
        """Extract package declaration."""
        package_node = self._find_child_by_type(root, self.PACKAGE_TYPE)
        if package_node:
            # Find the qualified name
            for child in package_node.children:
                if child.type == "scoped_identifier":
                    return self._get_node_text(parse_result, child)
        return ""
    
    def _extract_imports(self, root: Node, parse_result: ParseResult) -> List[str]:
        """Extract import statements."""
        imports = []
        for import_node in self._find_nodes_by_types(root, self.IMPORT_TYPES):
            for child in import_node.children:
                if child.type == "scoped_identifier":
                    imports.append(self._get_node_text(parse_result, child))
        return imports
    
    def _extract_class_symbols(self, class_node: Node, parse_result: ParseResult,
                               package_name: str, imports: List[str]) -> List[URMSymbol]:
        """Extract all symbols from a class/interface/enum/record."""
        symbols = []

        # Test detection from source path (mirrors Maven/Gradle conventions)
        norm_path = parse_result.file_path.replace("\\", "/").lower()
        path_is_test = "/src/test/" in norm_path

        # Get class name
        name_node = self._find_child_by_type(class_node, "identifier", "type_identifier")
        if not name_node:
            return symbols
        
        class_name = self._get_node_text(parse_result, name_node)
        qualified_name = f"{package_name}.{class_name}" if package_name else class_name
        
        # Determine kind and stereotype
        kind, stereotype = self._classify_class(class_node, class_name)
        if path_is_test or class_name.endswith(("Test", "Tests")):
            stereotype = "Test"
        
        # Create class symbol
        location = self._create_location(parse_result, class_node)
        class_symbol = URMSymbol(
            id=self._generate_symbol_id(class_name, "java"),
            name=class_name,
            qualified_name=qualified_name,
            kind=kind,
            language="java",
            location=location,
            stereotype=stereotype,
            annotations=self._extract_annotations(class_node, parse_result),
            modifiers=self._extract_modifiers(class_node),
            is_static="static" in self._extract_modifiers(class_node),
            is_abstract="abstract" in self._extract_modifiers(class_node),
        )
        symbols.append(class_symbol)
        
        # Extract class body members
        body_node = self._find_child_by_type(class_node, "class_body", "interface_body", "enum_body", "record_body")
        if body_node:
            # Fields
            for field_node in self._find_nodes_by_types(body_node, self.FIELD_TYPES):
                field_symbols = self._extract_field_symbols(field_node, parse_result, class_symbol, package_name)
                symbols.extend(field_symbols)
            
            # Methods
            for method_node in self._find_nodes_by_types(body_node, self.METHOD_TYPES):
                method_symbol = self._extract_method_symbol(method_node, parse_result, package_name, class_symbol)
                if method_symbol:
                    symbols.append(method_symbol)
        
        return symbols
    
    def _classify_class(self, class_node: Node, class_name: str) -> tuple:
        """Determine SymbolKind and stereotype for a class."""
        node_type = class_node.type
        annotations = self._extract_annotations(class_node, None)
        modifiers = self._extract_modifiers(class_node)
        
        # Check for stereotypes via annotations
        spring_stereotypes = {
            "RestController": "Controller",
            "Controller": "Controller",
            "Service": "Service",
            "Repository": "Repository",
            "Component": "Component",
            "Configuration": "Configuration",
            "Entity": "Entity",
            "ControllerAdvice": "Controller",
            "RestControllerAdvice": "Controller",
        }
        
        for ann in annotations:
            if ann in spring_stereotypes:
                return SymbolKind.CLASS, spring_stereotypes[ann]
        
        # Check for JPA Entity
        if "Entity" in annotations or "Table" in annotations:
            return SymbolKind.CLASS, "Entity"
        
        # Check for Spring Data Repository
        if "Repository" in class_name or "Dao" in class_name:
            return SymbolKind.INTERFACE, "Repository"
        
        # By node type
        if node_type == "interface_declaration":
            return SymbolKind.INTERFACE, "Interface"
        elif node_type == "enum_declaration":
            return SymbolKind.ENUM, "Enum"
        elif node_type == "record_declaration":
            return SymbolKind.STRUCT, "Record"
        
        # Check modifiers
        if "abstract" in modifiers:
            return SymbolKind.CLASS, "AbstractClass"
        
        return SymbolKind.CLASS, "Class"
    
    def _get_modifiers_node(self, node: Node) -> Optional[Node]:
        """Get the modifiers child of a declaration node (annotations live inside it)."""
        return self._find_child_by_type(node, "modifiers")

    def _extract_modifiers(self, node: Node) -> List[str]:
        """Extract keyword modifiers (public/final/static/abstract...) from a node."""
        modifiers = []
        mod_node = self._get_modifiers_node(node)
        if not mod_node:
            return modifiers
        for mod in mod_node.children:
            if mod.type in self.ANNOTATION_TYPES:
                continue  # annotations handled separately
            text = self._get_node_text_from_source(mod)
            if text and len(text) < 20:
                modifiers.append(text)
        return modifiers

    def _extract_annotations(self, node: Node, parse_result: Optional[ParseResult]) -> List[str]:
        """Extract annotation names from a node (they live inside the modifiers node)."""
        annotations = []
        mod_node = self._get_modifiers_node(node)
        if not mod_node:
            return annotations
        for child in mod_node.children:
            if child.type in self.ANNOTATION_TYPES:
                for ann_child in child.children:
                    if ann_child.type == "identifier":
                        annotations.append(self._get_node_text_from_source(ann_child))
                        break
        return annotations

    def _find_annotation_nodes(self, node: Node) -> List[Node]:
        """Find all annotation nodes attached to a declaration (inside modifiers)."""
        found = []
        mod_node = self._get_modifiers_node(node)
        if not mod_node:
            return found
        for child in mod_node.children:
            if child.type in self.ANNOTATION_TYPES:
                found.append(child)
        return found

    def _annotation_name(self, ann_node: Node, parse_result: ParseResult) -> Optional[str]:
        """Get the simple name of an annotation node."""
        for child in ann_node.children:
            if child.type == "identifier":
                return self._get_node_text(parse_result, child)
            if child.type == "scoped_identifier":
                # take last identifier segment
                ids = [c for c in child.children if c.type == "identifier"]
                if ids:
                    return self._get_node_text(parse_result, ids[-1])
        return None

    def _annotation_string_values(self, ann_node: Node, parse_result: ParseResult) -> List[str]:
        """Extract string literal values from an annotation argument list."""
        values = []
        for child in ann_node.children:
            if child.type == "annotation_argument_list":
                def collect(n):
                    if n.type == "string_fragment":
                        values.append(self._get_node_text(parse_result, n))
                    elif n.type == "string_literal":
                        # fallback: strip quotes from full literal
                        raw = self._get_node_text(parse_result, n).strip('"')
                        if raw and '"' not in raw:
                            values.append(raw)
                    for c in n.children:
                        collect(c)
                collect(child)
        return values
    
    def _extract_field_symbols(self, field_node: Node, parse_result: ParseResult,
                               class_symbol: URMSymbol, package_name: str) -> List[URMSymbol]:
        """Extract field symbols from field declaration."""
        symbols = []
        location = self._create_location(parse_result, field_node)
        
        # Get field type
        type_node = self._find_child_by_type(field_node, "type_identifier", "generic_type", "array_type")
        field_type = self._get_node_text(parse_result, type_node) if type_node else ""
        
        # Get variable declarators
        for child in field_node.children:
            if child.type == "variable_declarator":
                name_node = self._find_child_by_type(child, "identifier")
                if name_node:
                    field_name = self._get_node_text(parse_result, name_node)
                    field_symbol = URMSymbol(
                        id=self._generate_symbol_id(f"{class_symbol.name}_{field_name}", "java"),
                        name=field_name,
                        qualified_name=f"{class_symbol.qualified_name}.{field_name}",
                        kind=SymbolKind.FIELD,
                        language="java",
                        location=location,
                        signature=field_type,
                        modifiers=self._extract_modifiers(field_node),
                        annotations=self._extract_annotations(field_node, parse_result),
                        is_static="static" in self._extract_modifiers(field_node),
                        is_final="final" in self._extract_modifiers(field_node),
                        metadata={"parent_class": class_symbol.id, "field_type": field_type},
                    )
                    symbols.append(field_symbol)
        return symbols
    
    def _extract_method_symbol(self, method_node: Node, parse_result: ParseResult,
                               package_name: str, parent_class: Optional[URMSymbol]) -> Optional[URMSymbol]:
        """Extract method/constructor symbol."""
        name_node = self._find_child_by_type(method_node, "identifier")
        if not name_node:
            return None
        
        method_name = self._get_node_text(parse_result, name_node)
        location = self._create_location(parse_result, method_node)
        
        # Get return type
        return_type = ""
        type_node = self._find_child_by_type(method_node, "type_identifier", "generic_type", "void_type", "array_type")
        if type_node:
            return_type = self._get_node_text(parse_result, type_node)
        
        # Get parameters
        params = []
        param_node = self._find_child_by_type(method_node, "formal_parameters")
        if param_node:
            for child in param_node.children:
                if child.type == "formal_parameter":
                    param_type = ""
                    param_name = ""
                    for pchild in child.children:
                        if pchild.type in ("type_identifier", "generic_type", "array_type"):
                            param_type = self._get_node_text(parse_result, pchild)
                        elif pchild.type == "identifier":
                            param_name = self._get_node_text(parse_result, pchild)
                    params.append({"name": param_name, "type": param_type})
        
        # Build signature
        param_str = ", ".join([f"{p['name']}: {p['type']}" for p in params])
        signature = f"{method_name}({param_str}) -> {return_type}" if return_type else f"{method_name}({param_str})"
        
        # Determine kind
        is_constructor = method_node.type == "constructor_declaration"
        kind = SymbolKind.CONSTRUCTOR if is_constructor else SymbolKind.METHOD
        
        # Stereotype
        stereotype = "Constructor" if is_constructor else "Method"
        if parent_class and parent_class.stereotype == "Controller":
            stereotype = "Endpoint"
        
        qualified_name = f"{parent_class.qualified_name}.{method_name}" if parent_class else f"{package_name}.{method_name}"
        
        return URMSymbol(
            id=self._generate_symbol_id(f"{parent_class.name}_{method_name}" if parent_class else method_name, "java"),
            name=method_name,
            qualified_name=qualified_name,
            kind=kind,
            language="java",
            location=location,
            signature=signature,
            stereotype=stereotype,
            annotations=self._extract_annotations(method_node, parse_result),
            modifiers=self._extract_modifiers(method_node),
            is_static="static" in self._extract_modifiers(method_node),
            is_async=False,
            metadata={
                "parent_class": parent_class.id if parent_class else None,
                "return_type": return_type,
                "parameters": params,
            },
        )
    
    def extract_relationships(self, parse_result: ParseResult,
                              symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract relationships from Java file."""
        relationships = []
        root = parse_result.root_node
        if not root:
            return relationships
        
        symbol_map = {s.qualified_name: s for s in symbols}
        symbol_by_name = {s.name: s for s in symbols}
        
        # Get package
        package_name = self._extract_package(root, parse_result)
        
        # Process each class symbol
        for symbol in symbols:
            if symbol.kind not in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.ENUM, SymbolKind.STRUCT):
                continue
            
            # Find the class node
            class_node = self._find_class_node(root, symbol.name)
            if not class_node:
                continue
            
            # Extends relationship
            extends = self._extract_extends(class_node, parse_result)
            for ext in extends:
                self._add_relationship(relationships, symbol, ext, 
                                     RelationshipType.EXTENDS, parse_result, package_name)
            
            # Implements relationship
            implements = self._extract_implements(class_node, parse_result)
            for impl in implements:
                self._add_relationship(relationships, symbol, impl,
                                     RelationshipType.IMPLEMENTS, parse_result, package_name)
            
            # Field dependencies (injected fields)
            field_deps = self._extract_field_dependencies(class_node, parse_result, package_name)
            for dep in field_deps:
                self._add_relationship(relationships, symbol, dep,
                                     RelationshipType.DEPENDS_ON, parse_result, package_name)
        
        return relationships
    
    def _find_class_node(self, root: Node, class_name: str) -> Optional[Node]:
        """Find class node by name."""
        for node in self._find_nodes_by_types(root, self.CLASS_TYPES):
            name_node = self._find_child_by_type(node, "identifier", "type_identifier")
            if name_node and self._get_node_text_from_source(name_node) == class_name:
                return node
        return None
    
    def _extract_extends(self, class_node: Node, parse_result: ParseResult) -> List[str]:
        """Extract extends clause."""
        extends = []
        for child in class_node.children:
            if child.type == "superclass":
                for c in child.children:
                    if c.type in ("type_identifier", "generic_type"):
                        extends.append(self._get_node_text(parse_result, c))
        return extends
    
    def _extract_implements(self, class_node: Node, parse_result: ParseResult) -> List[str]:
        """Extract implements clause."""
        implements = []
        for child in class_node.children:
            if child.type == "super_interfaces":
                for c in child.children:
                    if c.type in ("type_identifier", "generic_type"):
                        implements.append(self._get_node_text(parse_result, c))
        return implements
    
    def _extract_field_dependencies(self, class_node: Node, parse_result: ParseResult,
                                    package_name: str) -> List[str]:
        """Extract field-level dependencies (injected fields).

        Detects:
          - @Autowired / @Inject / @Resource annotated fields
          - private final fields (Lombok @RequiredArgsConstructor pattern)
          - constructor parameter types
        """
        _PRIMITIVES = {"String", "str", "int", "Integer", "long", "Long", "double", "Double",
                       "float", "Float", "boolean", "Boolean", "bool", "short", "Short", "byte",
                       "Byte", "char", "Character", "void", "Object", "object"}

        def _keep(type_name):
            t = (type_name or "").strip().split("<")[0].split("[")[0]
            return bool(t) and t not in _PRIMITIVES and t[:1].isupper()

        deps = []
        body_node = self._find_child_by_type(class_node, "class_body")
        if not body_node:
            return deps

        # Constructor injection
        for ctor in self._find_nodes_by_types(body_node, {"constructor_declaration"}):
            params_node = self._find_child_by_type(ctor, "formal_parameters")
            if params_node:
                for param in params_node.children:
                    if param.type == "formal_parameter":
                        t = self._find_child_by_type(param, "type_identifier", "generic_type", "scoped_type_identifier")
                        if t:
                            name = self._get_node_text(parse_result, t)
                            if _keep(name) and name not in deps:
                                deps.append(name)

        # Field injection (@Autowired etc.) and private final fields
        for field_node in self._find_nodes_by_types(body_node, self.FIELD_TYPES):
            annotations = self._extract_annotations(field_node, parse_result)
            modifiers = self._extract_modifiers(field_node)
            is_injected = any(ann in ("Autowired", "Inject", "Resource") for ann in annotations)
            is_final_private = "final" in modifiers and "private" in modifiers
            if is_injected or is_final_private:
                type_node = self._find_child_by_type(field_node, "type_identifier", "generic_type", "scoped_type_identifier")
                if type_node:
                    name = self._get_node_text(parse_result, type_node)
                    if _keep(name) and name not in deps:
                        deps.append(name)

        return deps

    def _add_relationship(self, relationships: List[URMRelationship],
                         source: URMSymbol, target_name: str, rel_type: RelationshipType,
                         parse_result: ParseResult, package_name: str):
        """Add relationship with unresolved target name (resolved at graph build)."""
        target_qname = f"{package_name}.{target_name}" if package_name else target_name
        relationships.append(URMRelationship(
            source_id=source.id,
            target_id=target_name,  # Will be resolved later
            relationship_type=rel_type,
            language="java",
            location=self._create_location(parse_result, parse_result.root_node) if parse_result.root_node else None,
            metadata={"target_name": target_name, "target_qualified": target_qname},
        ))

    def _combine_paths(self, base: Optional[str], sub: Optional[str]) -> str:
        """Combine a class-level base path with a method-level path."""
        base_clean = (base or "").rstrip("/")
        sub_clean = (sub or "").lstrip("/")
        if not base_clean and not sub_clean:
            return "/"
        if not base_clean:
            return "/" + sub_clean
        if not sub_clean:
            return base_clean
        return f"{base_clean}/{sub_clean}"

    def _class_base_path(self, class_node: Node, parse_result: ParseResult) -> Optional[str]:
        """Extract class-level @RequestMapping base path."""
        for ann in self._find_annotation_nodes(class_node):
            name = self._annotation_name(ann, parse_result)
            if name == "RequestMapping":
                values = self._annotation_string_values(ann, parse_result)
                if values:
                    return values[0]
        return None

    def extract_endpoints(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMEndpoint]:
        """Extract REST endpoints from Spring MVC annotations."""
        endpoints = []
        root = parse_result.root_node
        if not root:
            return endpoints

        endpoint_annotations = {
            "GetMapping": "GET",
            "PostMapping": "POST",
            "PutMapping": "PUT",
            "DeleteMapping": "DELETE",
            "PatchMapping": "PATCH",
        }

        symbol_lookup = {}
        for s in symbols:
            if s.kind == SymbolKind.METHOD:
                symbol_lookup.setdefault(s.name, []).append(s)

        # Find methods with endpoint annotations anywhere in the file
        for method_node in self._find_nodes_by_types(root, {"method_declaration"}):
            for ann in self._find_annotation_nodes(method_node):
                ann_name = self._annotation_name(ann, parse_result)

                http_method = None
                path = None
                if ann_name in endpoint_annotations:
                    http_method = endpoint_annotations[ann_name]
                    values = self._annotation_string_values(ann, parse_result)
                    path = values[0] if values else ""
                elif ann_name == "RequestMapping":
                    # Method-level RequestMapping: check method= attribute crudely via all strings
                    values = self._annotation_string_values(ann, parse_result)
                    if values:
                        http_method = "REQUEST"
                        path = values[0]

                if not http_method:
                    continue

                # Resolve method + enclosing class names
                name_node = None
                for child in method_node.children:
                    if child.type == "identifier":
                        name_node = child
                        break
                method_name = self._get_node_text(parse_result, name_node) if name_node else ""

                parent_class = method_node.parent
                while parent_class is not None and parent_class.type not in self.CLASS_TYPES:
                    parent_class = parent_class.parent

                class_name = ""
                handler_symbol = None
                if parent_class:
                    cname_node = None
                    for child in parent_class.children:
                        if child.type == "identifier":
                            cname_node = child
                            break
                    class_name = self._get_node_text(parse_result, cname_node) if cname_node else ""

                candidates = symbol_lookup.get(method_name, [])
                for cand in candidates:
                    parent_ref = str(cand.metadata.get("parent_class") or "")
                    # Exact simple-name match on the synthetic parent id
                    # (java_OwnerController_345 -> OwnerController), never
                    # substring: "User" must not match "UserService".
                    simple = re.sub(r"^([a-z]{2,10})_(.+?)_(\d+)$",
                                    lambda m: m.group(2).split(".")[-1], parent_ref)
                    if parent_ref and class_name and simple == class_name:
                        handler_symbol = cand
                        break
                if handler_symbol is None and len(candidates) == 1:
                    handler_symbol = candidates[0]
                if handler_symbol is None and candidates:
                    handler_symbol = candidates[0]

                base_path = self._class_base_path(parent_class, parse_result) if parent_class else None
                full_path = self._combine_paths(base_path, path)

                endpoints.append(URMEndpoint(
                    route=full_path,
                    http_method=http_method,
                    handler_symbol_id=handler_symbol.id if handler_symbol else "",
                    framework="Spring MVC",
                    location=self._create_location(parse_result, method_node),
                ))
                # No break: one method may carry several mapping annotations.

        return endpoints
    
    def extract_configuration(self, parse_result: ParseResult) -> List[URMConfiguration]:
        """Extract configuration from Java config files."""
        configs = []
        # Check if this is a configuration file
        path = Path(parse_result.file_path)
        config_patterns = ["application.properties", "application.yml", "application.yaml",
                          "application-dev.properties", "application-prod.properties"]
        
        if path.name in config_patterns:
            # Parse properties/YAML
            lines = parse_result.source_code.splitlines()
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    configs.append(URMConfiguration(
                        file_path=parse_result.file_path,
                        config_type="properties",
                        key=key.strip(),
                        value=value.strip(),
                        location=SourceLocation(
                            file_path=parse_result.file_path,
                            start_line=i + 1,
                            start_column=1,
                            end_line=i + 1,
                            end_column=len(line) + 1,
                        ),
                        is_secret=self._is_secret_key(key.strip()),
                    ))
        return configs
    
    def _is_secret_key(self, key: str) -> bool:
        """Check if configuration key is likely a secret."""
        secret_patterns = ["password", "secret", "key", "token", "api_key", "apikey",
                          "private", "credential", "auth"]
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in secret_patterns)
    
    def extract_frameworks(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMFramework]:
        """Detect Java frameworks."""
        frameworks = []
        root = parse_result.root_node
        if not root:
            return frameworks
        
        # Check for Spring Boot annotations
        spring_indicators = ["SpringBootApplication", "EnableAutoConfiguration", 
                           "ComponentScan", "SpringBootConfiguration"]
        content = parse_result.source_code
        
        if any(indicator in content for indicator in spring_indicators):
            frameworks.append(URMFramework(
                name="Spring Boot",
                language="java",
                evidence_files=[parse_result.file_path],
                evidence_symbols=[s.name for s in symbols if s.kind == SymbolKind.CLASS],
            ))
        
        # Check for Spring MVC
        if any(ann in content for ann in ["RestController", "Controller", "RequestMapping", "GetMapping"]):
            existing = next((f for f in frameworks if f.name == "Spring Boot"), None)
            if not existing:
                frameworks.append(URMFramework(
                    name="Spring MVC",
                    language="java",
                    evidence_files=[parse_result.file_path],
                    evidence_symbols=[s.name for s in symbols if s.stereotype == "Controller"],
                ))
        
        # Check for JPA
        if any(ann in content for ann in ["Entity", "Table", "Column", "Id", "GeneratedValue"]):
            frameworks.append(URMFramework(
                name="JPA/Hibernate",
                language="java",
                evidence_files=[parse_result.file_path],
                evidence_symbols=[s.name for s in symbols if s.stereotype == "Entity"],
            ))
        
        return frameworks
