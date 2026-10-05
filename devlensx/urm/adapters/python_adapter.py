"""
DevLensX Python Language Adapter
Translates Tree-sitter Python CST to Universal Repository Model.
"""

from typing import List, Dict, Any, Optional, Set
import re
from pathlib import Path
from tree_sitter import Node

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_valid_identifier(name: str) -> bool:
    """Guards against garbage symbol names from CST mis-extraction."""
    return bool(name) and bool(_IDENTIFIER_RE.match(name))

from devlensx.urm.adapters.base import (
    BaseLanguageAdapter, SupportedLanguage, SymbolKind, RelationshipType,
    URMSymbol, URMRelationship, URMEndpoint, URMConfiguration, URMFramework,
    SourceLocation, ParseResult
)


class PythonLanguageAdapter(BaseLanguageAdapter):
    """Python language adapter using Tree-sitter."""
    
    def __init__(self):
        super().__init__(SupportedLanguage.PYTHON)
        
        # Python node types
        self.CLASS_TYPES = {"class_definition"}
        self.FUNCTION_TYPES = {"function_definition", "async_function_definition", "decorated_definition"}
        self.DECORATOR_TYPES = {"decorator"}
        self.IMPORT_TYPES = {"import_statement", "import_from_statement"}
        self.ASSIGNMENT_TYPES = {"assignment", "annotated_assignment"}
        self.CALL_TYPES = {"call"}
        self.COMPREHENSION_TYPES = {"list_comprehension", "dict_comprehension", "set_comprehension"}
    
    def get_file_extensions(self) -> tuple:
        return (".py",)
    
    def extract_symbols(self, parse_result: ParseResult) -> List[URMSymbol]:
        """Extract symbols from Python file."""
        symbols = []
        root = parse_result.root_node
        if not root:
            return symbols
        
        module_name = self._get_module_name(parse_result)
        
        # Extract imports first
        imports = self._extract_imports(root, parse_result)
        
        # Classes
        for class_node in self._find_nodes_by_types(root, self.CLASS_TYPES):
            class_symbols = self._extract_class_symbols(class_node, parse_result, module_name, imports)
            symbols.extend(class_symbols)
        
        # Functions (not in classes) - includes both regular and decorated functions
        for func_node in self._find_nodes_by_types(root, self.FUNCTION_TYPES):
            parent = func_node.parent
            # Only module-level functions
            if parent and parent.type == "module":
                func_symbol = self._extract_function_symbol(func_node, parse_result, module_name, None)
                if func_symbol:
                    symbols.append(func_symbol)
        
        # Also handle decorated functions at module level
        for decorated_node in self._find_nodes_by_types(root, {"decorated_definition"}):
            parent = decorated_node.parent
            if parent and parent.type == "module":
                # Find the actual function inside the decorated_definition
                for child in decorated_node.children:
                    if child.type in ("function_definition", "async_function_definition"):
                        func_symbol = self._extract_function_symbol(child, parse_result, module_name, None)
                        if func_symbol:
                            # Add decorators from the decorated_definition, then
                            # re-decide endpoint stereotype + route path, since the
                            # inner function node carries no decorator children.
                            for dec_child in decorated_node.children:
                                if dec_child.type == "decorator":
                                    dec_text = self._get_node_text(parse_result, dec_child).replace("@", "")
                                    if dec_text not in func_symbol.annotations:
                                        func_symbol.annotations.append(dec_text)
                            route = self._parse_route_decorator(func_symbol.annotations)
                            if route is not None:
                                func_symbol.stereotype = "Endpoint"
                                func_symbol.metadata["route_path"] = route[1]
                                func_symbol.metadata["route_method"] = route[0]
                            symbols.append(func_symbol)
                            break
        
        # Module-level variables/constants
        for assign_node in self._find_nodes_by_types(root, self.ASSIGNMENT_TYPES):
            # Only module-level
            parent = assign_node.parent
            if parent and parent.type == "module":
                var_symbols = self._extract_assignment_symbols(assign_node, parse_result, module_name)
                symbols.extend(var_symbols)
        
        return symbols
    
    def _get_module_name(self, parse_result: ParseResult) -> str:
        """Get module name from file path."""
        path = Path(parse_result.file_path)
        # Remove .py extension
        return path.stem
    
    def _extract_imports(self, root: Node, parse_result: ParseResult) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        
        for import_node in self._find_nodes_by_types(root, self.IMPORT_TYPES):
            if import_node.type == "import_statement":
                # import module
                for child in import_node.children:
                    if child.type == "dotted_name":
                        module = self._get_node_text(parse_result, child)
                        imports.append({"module": module, "names": [module], "alias": None})
                    elif child.type == "aliased_import":
                        # import module as alias
                        for c in child.children:
                            if c.type == "dotted_name":
                                module = self._get_node_text(parse_result, c)
                            elif c.type == "identifier":
                                alias = self._get_node_text(parse_result, c)
                                imports.append({"module": module, "names": [module], "alias": alias})
            
            elif import_node.type == "import_from_statement":
                # from module import name
                module = ""
                names = []
                
                for child in import_node.children:
                    if child.type == "dotted_name":
                        module = self._get_node_text(parse_result, child)
                    elif child.type == "wildcard_import":
                        names = ["*"]
                    elif child.type == "import_list":
                        for c in child.children:
                            if c.type == "identifier":
                                names.append(self._get_node_text(parse_result, c))
                            elif c.type == "aliased_import":
                                for cc in c.children:
                                    if cc.type == "identifier":
                                        names.append(self._get_node_text(parse_result, cc))
                
                for name in names:
                    imports.append({"module": module, "names": [name], "alias": None})
        
        return imports
    
    def _extract_class_symbols(self, class_node: Node, parse_result: ParseResult,
                               module_name: str, imports: List[Dict]) -> List[URMSymbol]:
        """Extract class and its members."""
        symbols = []
        
        name_node = self._find_child_by_type(class_node, "identifier")
        if not name_node:
            return symbols
        
        class_name = self._get_node_text(parse_result, name_node)
        if not _is_valid_identifier(class_name):
            return symbols
        location = self._create_location(parse_result, class_node)
        
        # Get decorators
        decorators = []
        for child in class_node.children:
            if child.type == "decorator":
                decorators.append(self._get_node_text(parse_result, child).replace("@", ""))
        
        # Get base classes
        bases = []
        for child in class_node.children:
            if child.type == "argument_list":
                for c in child.children:
                    if c.type == "identifier":
                        bases.append(self._get_node_text(parse_result, c))
        
        # Determine stereotype
        stereotype = self._classify_python_class(class_name, decorators, bases)
        
        class_symbol = URMSymbol(
            id=self._generate_symbol_id(class_name, "py"),
            name=class_name,
            qualified_name=f"{module_name}.{class_name}",
            kind=SymbolKind.CLASS,
            language="python",
            location=location,
            stereotype=stereotype,
            annotations=decorators,
            metadata={
                "bases": bases,
                "is_abstract": self._is_abstract_class(class_node, parse_result),
            },
        )
        symbols.append(class_symbol)
        
        # Extract class body
        body_node = self._find_child_by_type(class_node, "block")
        if body_node:
            for child in body_node.children:
                if child.type == "function_definition" or child.type == "async_function_definition":
                    method_symbol = self._extract_function_symbol(child, parse_result, module_name, class_symbol)
                    if method_symbol:
                        symbols.append(method_symbol)
                elif child.type in ("assignment", "annotated_assignment"):
                    # Class attributes
                    attr_symbols = self._extract_assignment_symbols(child, parse_result, module_name, class_symbol)
                    symbols.extend(attr_symbols)
        
        return symbols
    
    def _classify_python_class(self, class_name: str, decorators: List[str], bases: List[str]) -> str:
        """Classify Python class based on decorators, bases, and naming."""
        # Framework decorators
        decorator_map = {
            "dataclass": "DataClass",
            "attr.s": "DataClass",
            "pydantic.BaseModel": "Model",
            "BaseModel": "Model",
            "django.db.models.Model": "Model",
            "sqlalchemy.orm.DeclarativeBase": "Entity",
            "Component": "Component",
            "Service": "Service",
            "Repository": "Repository",
            "Controller": "Controller",
            "APIRouter": "Router",
            "FastAPI": "Application",
        }
        
        for dec in decorators:
            for key, value in decorator_map.items():
                if key in dec:
                    return value
        
        # Check base classes
        for base in bases:
            if "Model" in base or "Entity" in base:
                return "Model"
            if "Base" in base and "Service" in base:
                return "Service"
            if "Controller" in base:
                return "Controller"
        
        # Naming conventions
        name_lower = class_name.lower()
        if "service" in name_lower:
            return "Service"
        elif "repository" in name_lower or "dao" in name_lower:
            return "Repository"
        elif "controller" in name_lower or "view" in name_lower or "handler" in name_lower:
            return "Controller"
        elif "model" in name_lower or "entity" in name_lower or "schema" in name_lower:
            return "Model"
        elif "config" in name_lower or "settings" in name_lower:
            return "Configuration"
        elif "exception" in name_lower or "error" in name_lower:
            return "Exception"
        elif "test" in name_lower:
            return "Test"
        elif "util" in name_lower or "helper" in name_lower or "mixin" in name_lower:
            return "Utility"
        
        return "Class"
    
    def _is_abstract_class(self, class_node: Node, parse_result: ParseResult) -> bool:
        """Check if class is abstract (has ABC metaclass or abstractmethod)."""
        for child in class_node.children:
            if child.type == "argument_list":
                for c in child.children:
                    if c.type == "identifier" and "ABC" in self._get_node_text(parse_result, c):
                        return True
        
        # Check for @abstractmethod in methods
        body_node = self._find_child_by_type(class_node, "block")
        if body_node:
            for child in body_node.children:
                if child.type in ("function_definition", "async_function_definition"):
                    for c in child.children:
                        if c.type == "decorator":
                            if "abstractmethod" in self._get_node_text(parse_result, c):
                                return True
        return False
    
    def _extract_function_symbol(self, func_node: Node, parse_result: ParseResult,
                                 module_name: str, parent_class: Optional[URMSymbol]) -> Optional[URMSymbol]:
        """Extract function/method symbol."""
        name_node = self._find_child_by_type(func_node, "identifier")
        if not name_node:
            return None
        
        func_name = self._get_node_text(parse_result, name_node)
        if not _is_valid_identifier(func_name):
            return None
        location = self._create_location(parse_result, func_node)
        
        # Get decorators
        decorators = []
        for child in func_node.children:
            if child.type == "decorator":
                decorators.append(self._get_node_text(parse_result, child).replace("@", ""))
        
        # Get parameters
        params = []
        return_type = ""
        
        for child in func_node.children:
            if child.type == "parameters":
                for param in child.children:
                    if param.type in ("identifier", "typed_parameter", "default_parameter"):
                        param_name = ""
                        param_type = ""
                        default_value = None
                        
                        if param.type == "identifier":
                            param_name = self._get_node_text(parse_result, param)
                        elif param.type == "typed_parameter":
                            for pchild in param.children:
                                if pchild.type == "identifier":
                                    param_name = self._get_node_text(parse_result, pchild)
                                elif pchild.type == "type_annotation":
                                    param_type = self._get_node_text(parse_result, pchild)
                        elif param.type == "default_parameter":
                            for pchild in param.children:
                                if pchild.type == "identifier":
                                    param_name = self._get_node_text(parse_result, pchild)
                                elif pchild.type == "type_annotation":
                                    param_type = self._get_node_text(parse_result, pchild)
                        
                        params.append({"name": param_name, "type": param_type, "default": default_value})
            
            elif child.type == "return_type":
                return_type = self._get_node_text(parse_result, child).replace("->", "").strip()
        
        param_str = ", ".join([f"{p['name']}: {p['type']}" for p in params])
        signature = f"{func_name}({param_str})" + (f" -> {return_type}" if return_type else "")
        
        # Determine kind and stereotype
        is_async = func_node.type == "async_function_definition"
        is_method = parent_class is not None
        
        if is_method:
            kind = SymbolKind.METHOD
            stereotype = "Method"
            if func_name == "__init__":
                kind = SymbolKind.CONSTRUCTOR
                stereotype = "Constructor"
            elif func_name.startswith("__") and func_name.endswith("__"):
                stereotype = "DunderMethod"
        else:
            kind = SymbolKind.FUNCTION
            # Check for route decorators
            is_route = any(dec in ("get", "post", "put", "delete", "patch", "route", "api_route") for dec in decorators)
            if is_route:
                stereotype = "Endpoint"
            elif func_name.startswith("test_"):
                stereotype = "Test"
            elif func_name.startswith("_"):
                stereotype = "PrivateFunction"
            else:
                stereotype = "Function"
        
        qualified_name = f"{parent_class.qualified_name}.{func_name}" if parent_class else f"{module_name}.{func_name}"
        
        return URMSymbol(
            id=self._generate_symbol_id(f"{parent_class.name}_{func_name}" if parent_class else func_name, "py"),
            name=func_name,
            qualified_name=qualified_name,
            kind=kind,
            language="python",
            location=location,
            signature=signature,
            stereotype=stereotype,
            annotations=decorators,
            is_async=is_async,
            metadata={
                "parent_class": parent_class.id if parent_class else None,
                "parameters": params,
                "return_type": return_type,
                "decorators": decorators,
            },
        )
    
    @staticmethod
    def _parse_route_decorator(annotations) -> Optional[tuple]:
        """Detect a route decorator (app.get("/x"), @route(...)) and return
        (METHOD, path). String-literal first argument is the route path."""
        import re as _re
        for dec in annotations or []:
            m = _re.search(r"\.?(get|post|put|delete|patch|route|api_route)\s*\(", str(dec), re.IGNORECASE)
            if not m:
                continue
            method = {"get": "GET", "post": "POST", "put": "PUT",
                      "delete": "DELETE", "patch": "PATCH"}.get(m.group(1).lower(), "GET")
            sm = _re.search(r"""['"](/[^'"]*)['"]""", str(dec))
            path = sm.group(1) if sm else ""
            return method, path
        return None

    def _extract_assignment_symbols(self, assign_node: Node, parse_result: ParseResult,
                                  module_name: str, parent_class: Optional[URMSymbol] = None) -> List[URMSymbol]:
        """Extract variable/constant assignments."""
        symbols = []
        location = self._create_location(parse_result, assign_node)
        
        if assign_node.type == "annotated_assignment":
            # x: Type = value
            name = ""
            type_ann = ""
            for child in assign_node.children:
                if child.type == "identifier":
                    name = self._get_node_text(parse_result, child)
                elif child.type == "type_annotation":
                    type_ann = self._get_node_text(parse_result, child).replace(":", "").strip()
            
            if name:
                is_constant = name.isupper()
                symbols.append(URMSymbol(
                    id=self._generate_symbol_id(name, "py"),
                    name=name,
                    qualified_name=(f"{module_name}.{parent_class.name}.{name}" if parent_class else f"{module_name}.{name}"),
                    kind=SymbolKind.CONSTANT if is_constant else SymbolKind.VARIABLE,
                    language="python",
                    location=location,
                    signature=type_ann,
                    stereotype="Constant" if is_constant else "Variable",
                    metadata={"parent_class": parent_class.id if parent_class else None, "type": type_ann},
                ))
        
        elif assign_node.type == "assignment":
            # x = value
            left = assign_node.child_by_field_name("left")
            if left and left.type == "identifier":
                name = self._get_node_text(parse_result, left)
                is_constant = name.isupper()
                symbols.append(URMSymbol(
                    id=self._generate_symbol_id(name, "py"),
                    name=name,
                    qualified_name=(f"{module_name}.{parent_class.name}.{name}" if parent_class else f"{module_name}.{name}"),
                    kind=SymbolKind.CONSTANT if is_constant else SymbolKind.VARIABLE,
                    language="python",
                    location=location,
                    stereotype="Constant" if is_constant else "Variable",
                    metadata={"parent_class": parent_class.id if parent_class else None},
                ))
            elif left and left.type == "tuple":
                # Multiple assignment: x, y = ...
                for child in left.children:
                    if child.type == "identifier":
                        name = self._get_node_text(parse_result, child)
                        is_constant = name.isupper()
                        symbols.append(URMSymbol(
                            id=self._generate_symbol_id(name, "py"),
                            name=name,
                            qualified_name=(f"{module_name}.{parent_class.name}.{name}" if parent_class else f"{module_name}.{name}"),
                            kind=SymbolKind.CONSTANT if is_constant else SymbolKind.VARIABLE,
                            language="python",
                            location=location,
                            stereotype="Constant" if is_constant else "Variable",
                            metadata={"parent_class": parent_class.id if parent_class else None},
                        ))
        
        return symbols
    
    def extract_relationships(self, parse_result: ParseResult,
                              symbols: List[URMSymbol]) -> List[URMRelationship]:
        """Extract relationships from Python file."""
        relationships = []
        root = parse_result.root_node
        if not root:
            return relationships
        
        symbol_by_name = {s.name: s for s in symbols}
        symbol_by_qname = {s.qualified_name: s for s in symbols}
        
        # Class inheritance
        for symbol in symbols:
            if symbol.kind == SymbolKind.CLASS:
                class_node = self._find_class_node(root, symbol.name)
                if class_node:
                    bases = symbol.metadata.get("bases", [])
                    for base in bases:
                        relationships.append(URMRelationship(
                            source_id=symbol.id,
                            target_id=base,
                            relationship_type=RelationshipType.EXTENDS,
                            language="python",
                        ))
        
        # Import relationships
        imports = self._extract_imports(root, parse_result)
        for symbol in symbols:
            for imp in imports:
                for name in imp.get("names", []):
                    if name in symbol_by_name or name in symbol_by_qname:
                        relationships.append(URMRelationship(
                            source_id=symbol.id,
                            target_id=name,
                            relationship_type=RelationshipType.IMPORTS,
                            language="python",
                        ))
        
        # Same-file CALLS relationships: caller -> callee via call nodes
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
        for call_node in self._find_nodes_by_types(root, {"call"}):
            func_child = call_node.child_by_field_name("function")
            if func_child is None:
                continue
            callee_text = ""
            if func_child.type == "identifier":
                callee_text = self._get_node_text(parse_result, func_child)
            elif func_child.type == "attribute":
                # method call: take the attribute name
                attr_node = func_child.child_by_field_name("attribute")
                if attr_node is not None:
                    callee_text = self._get_node_text(parse_result, attr_node)

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
                language="python",
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
            name_node = self._find_child_by_type(node, "identifier")
            if name_node and self._get_node_text_from_source(name_node) == class_name:
                return node
        return None
    
    def extract_endpoints(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMEndpoint]:
        """Extract API endpoints from route decorators."""
        endpoints = []
        
        # FastAPI/Flask/Django route decorators
        route_methods = {
            "get": "GET", "post": "POST", "put": "PUT",
            "delete": "DELETE", "patch": "PATCH", "route": "GET",
            "api_route": "GET",
        }
        
        for symbol in symbols:
            if symbol.stereotype == "Endpoint":
                method = "GET"
                for dec in symbol.annotations:
                    dec_lower = dec.lower().replace("@", "")
                    if dec_lower in route_methods:
                        method = route_methods[dec_lower]
                        break
                
                # Try to extract path from decorator metadata
                path = f"/{symbol.name}"
                if symbol.metadata.get("route_path"):
                    path = symbol.metadata["route_path"]
                
                endpoints.append(URMEndpoint(
                    route=path,
                    http_method=method,
                    handler_symbol_id=symbol.id,
                    framework="FastAPI/Flask/Django",
                    location=symbol.location,
                ))
        
        return endpoints
    
    def extract_configuration(self, parse_result: ParseResult) -> List[URMConfiguration]:
        """Extract configuration from Python config files."""
        configs = []
        path = Path(parse_result.file_path)
        
        config_files = {
            "requirements.txt": "pip",
            "pyproject.toml": "poetry",
            "setup.py": "setuptools",
            "setup.cfg": "setuptools",
            "Pipfile": "pipenv",
            "poetry.lock": "poetry",
            ".env": "env",
            ".env.local": "env",
            ".env.example": "env",
            "settings.py": "django",
            "config.py": "python",
        }
        
        if path.name in config_files:
            config_type = config_files[path.name]
            
            if path.name == "requirements.txt":
                lines = parse_result.source_code.splitlines()
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        configs.append(URMConfiguration(
                            file_path=parse_result.file_path,
                            config_type="pip",
                            key=line,
                            value="",
                            location=SourceLocation(
                                file_path=parse_result.file_path,
                                start_line=i + 1, start_column=1,
                                end_line=i + 1, end_column=len(line) + 1,
                            ),
                        ))
            elif path.name == "pyproject.toml":
                # Parse TOML
                try:
                    import toml
                    data = toml.loads(parse_result.source_code)
                    for key, value in self._flatten_dict(data).items():
                        configs.append(URMConfiguration(
                            file_path=parse_result.file_path,
                            config_type="toml",
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
    
    def _flatten_dict(self, d: Dict, parent_key: str = "") -> Dict[str, Any]:
        """Flatten nested dict."""
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key))
            else:
                items[new_key] = v
        return items
    
    def _is_secret_key(self, key: str) -> bool:
        secret_patterns = ["secret", "key", "token", "password", "api_key", "apikey",
                          "private", "credential", "auth", "database_url", "db_password"]
        return any(p in key.lower() for p in secret_patterns)
    
    def extract_frameworks(self, parse_result: ParseResult,
                          symbols: List[URMSymbol]) -> List[URMFramework]:
        """Detect Python frameworks."""
        frameworks = []
        content = parse_result.source_code
        path = Path(parse_result.file_path)
        
        # Check requirements.txt / pyproject.toml
        if path.name in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile"):
            framework_patterns = {
                "fastapi": "FastAPI",
                "flask": "Flask",
                "django": "Django",
                "starlette": "Starlette",
                "tornado": "Tornado",
                "bottle": "Bottle",
                "falcon": "Falcon",
                "aiohttp": "aiohttp",
                "sanic": "Sanic",
                "quart": "Quart",
                "litestar": "Litestar",
                "pydantic": "Pydantic",
                "sqlalchemy": "SQLAlchemy",
                "django.db": "Django ORM",
                "peewee": "Peewee",
                "tortoise-orm": "Tortoise ORM",
                "prisma": "Prisma",
                "celery": "Celery",
                "pytest": "pytest",
                "unittest": "unittest",
            }
            
            for pattern, framework in framework_patterns.items():
                if pattern in content.lower():
                    frameworks.append(URMFramework(
                        name=framework,
                        language="python",
                        evidence_files=[parse_result.file_path],
                    ))
        
        # Check for framework imports in code
        if "fastapi" in content.lower():
            frameworks.append(URMFramework(
                name="FastAPI", language="python", evidence_files=[parse_result.file_path],
            ))
        if "flask" in content.lower():
            frameworks.append(URMFramework(
                name="Flask", language="python", evidence_files=[parse_result.file_path],
            ))
        if "django" in content.lower():
            frameworks.append(URMFramework(
                name="Django", language="python", evidence_files=[parse_result.file_path],
            ))
        
        return frameworks


