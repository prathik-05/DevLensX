"""
DevLensX Shared Types
Common types used across parser and adapters to avoid circular imports.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field

import tree_sitter
from tree_sitter import Language, Parser, Node


class SupportedLanguage(str, Enum):
    """Languages with Tree-sitter grammars available."""
    JAVA = "java"
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    CSHARP = "c_sharp"
    CPP = "cpp"
    C = "c"
    PHP = "php"
    RUBY = "ruby"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    SCALA = "scala"
    DART = "dart"
    BASH = "bash"
    LUA = "lua"
    JSON = "json"
    TOML = "toml"
    YAML = "yaml"
    HTML = "html"
    CSS = "css"
    DOCKERFILE = "dockerfile"


@dataclass
class ParseResult:
    """Result of parsing a single file."""
    file_path: str
    language: SupportedLanguage
    root_node: Optional[Node] = None
    source_code: str = ""
    parse_errors: List[str] = field(default_factory=list)
    success: bool = False


# File extension to language mapping
EXTENSION_TO_LANGUAGE = {
    ".java": SupportedLanguage.JAVA,
    ".py": SupportedLanguage.PYTHON,
    ".ts": SupportedLanguage.TYPESCRIPT,
    ".tsx": SupportedLanguage.TYPESCRIPT,
    ".js": SupportedLanguage.JAVASCRIPT,
    ".jsx": SupportedLanguage.JAVASCRIPT,
    ".go": SupportedLanguage.GO,
    ".rs": SupportedLanguage.RUST,
    ".cs": SupportedLanguage.CSHARP,
    ".cpp": SupportedLanguage.CPP,
    ".cc": SupportedLanguage.CPP,
    ".cxx": SupportedLanguage.CPP,
    ".hpp": SupportedLanguage.CPP,
    ".h": SupportedLanguage.CPP,
    ".c": SupportedLanguage.C,
    ".php": SupportedLanguage.PHP,
    ".rb": SupportedLanguage.RUBY,
    ".kt": SupportedLanguage.KOTLIN,
    ".kts": SupportedLanguage.KOTLIN,
    ".swift": SupportedLanguage.SWIFT,
    ".scala": SupportedLanguage.SCALA,
    ".dart": SupportedLanguage.DART,
    ".sh": SupportedLanguage.BASH,
    ".bash": SupportedLanguage.BASH,
    ".lua": SupportedLanguage.LUA,
    ".json": SupportedLanguage.JSON,
    ".toml": SupportedLanguage.TOML,
    ".yaml": SupportedLanguage.YAML,
    ".yml": SupportedLanguage.YAML,
    ".html": SupportedLanguage.HTML,
    ".htm": SupportedLanguage.HTML,
    ".css": SupportedLanguage.CSS,
    ".scss": SupportedLanguage.CSS,
    ".sass": SupportedLanguage.CSS,
    ".dockerfile": SupportedLanguage.DOCKERFILE,
    "Dockerfile": SupportedLanguage.DOCKERFILE,
}

# Special filename mappings
FILENAME_TO_LANGUAGE = {
    "Dockerfile": SupportedLanguage.DOCKERFILE,
    "dockerfile": SupportedLanguage.DOCKERFILE,
    "Makefile": SupportedLanguage.BASH,
    "makefile": SupportedLanguage.BASH,
    "CMakeLists.txt": SupportedLanguage.BASH,
}


# Language to Tree-sitter language module mapping
TS_LANGUAGE_MODULES = {
    SupportedLanguage.JAVA: "tree_sitter_java",
    SupportedLanguage.PYTHON: "tree_sitter_python",
    SupportedLanguage.TYPESCRIPT: "tree_sitter_typescript",
    SupportedLanguage.JAVASCRIPT: "tree_sitter_javascript",
    SupportedLanguage.GO: "tree_sitter_go",
    SupportedLanguage.RUST: "tree_sitter_rust",
    SupportedLanguage.CSHARP: "tree_sitter_c_sharp",
    SupportedLanguage.CPP: "tree_sitter_cpp",
    SupportedLanguage.C: "tree_sitter_c",
    SupportedLanguage.PHP: "tree_sitter_php",
    SupportedLanguage.RUBY: "tree_sitter_ruby",
    SupportedLanguage.KOTLIN: "tree_sitter_kotlin",
    SupportedLanguage.SWIFT: "tree_sitter_swift",
    SupportedLanguage.SCALA: "tree_sitter_scala",
    SupportedLanguage.DART: "tree_sitter_dart",
    SupportedLanguage.BASH: "tree_sitter_bash",
    SupportedLanguage.LUA: "tree_sitter_lua",
    SupportedLanguage.JSON: "tree_sitter_json",
    SupportedLanguage.TOML: "tree_sitter_toml",
    SupportedLanguage.YAML: "tree_sitter_yaml",
    SupportedLanguage.HTML: "tree_sitter_html",
    SupportedLanguage.CSS: "tree_sitter_css",
    SupportedLanguage.DOCKERFILE: "tree_sitter_dockerfile",
}


class TreeSitterParser:
    """Central Tree-sitter parser manager."""

    def __init__(self):
        self._parsers: Dict[SupportedLanguage, Parser] = {}
        self._languages: Dict[SupportedLanguage, Language] = {}
        self._initialize_languages()

    def _initialize_languages(self):
        """Initialize Tree-sitter languages and parsers."""
        for lang_enum, module_name in TS_LANGUAGE_MODULES.items():
            try:
                module = __import__(module_name)
                
                # Special handling for TypeScript which has language_typescript and language_tsx
                if lang_enum in (SupportedLanguage.TYPESCRIPT, SupportedLanguage.JAVASCRIPT):
                    if lang_enum == SupportedLanguage.TYPESCRIPT:
                        lang_obj = getattr(module, "language_typescript", None)
                    else:
                        lang_obj = getattr(module, "language_javascript", None)
                    
                    if lang_obj is not None:
                        # TypeScript language functions return PyCapsule when called
                        if callable(lang_obj):
                            lang_ptr = lang_obj()
                        else:
                            lang_ptr = lang_obj
                        self._languages[lang_enum] = Language(lang_ptr)
                        parser = Parser(self._languages[lang_enum])
                        self._parsers[lang_enum] = parser
                        continue
                
                # Standard handling for other languages
                lang_func = getattr(module, "language", None)
                if lang_func is None:
                    # Try alternative naming
                    lang_func = getattr(module, "language_py", None)
                if lang_func is None:
                    # Try as property
                    lang_obj = getattr(module, "LANGUAGE", None)
                    if lang_obj is not None:
                        self._languages[lang_enum] = Language(lang_obj)
                        parser = Parser(self._languages[lang_enum])
                        self._parsers[lang_enum] = parser
                        continue
                
                if lang_func:
                    lang = Language(lang_func())
                    self._languages[lang_enum] = lang
                    parser = Parser(lang)
                    self._parsers[lang_enum] = parser
            except Exception as e:
                # Language not available, skip
                pass

    def get_parser(self, language: SupportedLanguage) -> Optional[Parser]:
        """Get parser for a language."""
        return self._parsers.get(language)

    def get_language(self, language: SupportedLanguage) -> Optional[Language]:
        """Get Tree-sitter language object."""
        return self._languages.get(language)

    def is_supported(self, language: SupportedLanguage) -> bool:
        """Check if language is supported."""
        return language in self._parsers

    def detect_language(self, file_path: str) -> Optional[SupportedLanguage]:
        """Detect language from file extension or name."""
        return detect_language(file_path)

    def parse_file(self, file_path: str) -> ParseResult:
        """Parse a single file and return ParseResult."""
        language = self.detect_language(file_path)
        if not language or not self.is_supported(language):
            return ParseResult(
                file_path=file_path,
                language=language or SupportedLanguage.JAVA,
                parse_errors=[f"Unsupported language for file: {file_path}"],
                success=False
            )

        parser = self._parsers[language]
        
        try:
            path = Path(file_path)
            source_bytes = path.read_bytes()
            source_code = source_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=language,
                parse_errors=[f"Failed to read file: {e}"],
                success=False
            )

        try:
            tree = parser.parse(source_bytes)
            root_node = tree.root_node
            
            # Check for parse errors
            parse_errors = []
            self._collect_parse_errors(root_node, parse_errors)
            
            return ParseResult(
                file_path=file_path,
                language=language,
                root_node=root_node,
                source_code=source_code,
                parse_errors=parse_errors,
                success=True
            )
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=language,
                parse_errors=[f"Parse failed: {e}"],
                success=False
            )

    def parse_file_from_source(self, file_path: str, source_code: str) -> ParseResult:
        """Parse source code directly without reading from a file."""
        language = self.detect_language(file_path)
        if not language or not self.is_supported(language):
            return ParseResult(
                file_path=file_path,
                language=language or SupportedLanguage.JAVA,
                parse_errors=[f"Unsupported language for file: {file_path}"],
                success=False
            )

        parser = self._parsers[language]
        
        try:
            source_bytes = source_code.encode("utf-8")
            tree = parser.parse(source_bytes)
            root_node = tree.root_node
            
            # Check for parse errors
            parse_errors = []
            self._collect_parse_errors(root_node, parse_errors)
            
            return ParseResult(
                file_path=file_path,
                language=language,
                root_node=root_node,
                source_code=source_code,
                parse_errors=parse_errors,
                success=True
            )
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=language,
                parse_errors=[f"Parse failed: {e}"],
                success=False
            )

    def _collect_parse_errors(self, node: Node, errors: List[str]):
        """Recursively collect parse errors from tree."""
        if node.type == "ERROR":
            errors.append(f"Parse error at {node.start_point}: {node.text[:50] if node.text else ''}")
        for child in node.children:
            self._collect_parse_errors(child, errors)

    def parse_repository(self, repo_path: str, 
                        exclude_patterns: Optional[List[str]] = None) -> List[ParseResult]:
        """Parse all supported files in a repository."""
        if exclude_patterns is None:
            exclude_patterns = [
                "node_modules", ".git", "__pycache__", "venv", "env",
                "dist", "build", "target", ".gradle", "bin", "obj",
                "vendor", ".venv", "venv", ".next", ".turbo"
            ]
        
        repo_root = Path(repo_path)
        results = []
        
        for file_path in repo_root.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Check exclusions
            relative = file_path.relative_to(repo_root)
            if any(pattern in str(relative) for pattern in exclude_patterns):
                continue
            
            # Check if language supported
            language = self.detect_language(str(file_path))
            if not language or not self.is_supported(language):
                continue
            
            result = self.parse_file(str(file_path))
            results.append(result)
        
        return results


# Language to Tree-sitter language module mapping
TS_LANGUAGE_MODULES = {
    SupportedLanguage.JAVA: "tree_sitter_java",
    SupportedLanguage.PYTHON: "tree_sitter_python",
    SupportedLanguage.TYPESCRIPT: "tree_sitter_typescript",
    SupportedLanguage.JAVASCRIPT: "tree_sitter_javascript",
    SupportedLanguage.GO: "tree_sitter_go",
    SupportedLanguage.RUST: "tree_sitter_rust",
    SupportedLanguage.CSHARP: "tree_sitter_c_sharp",
    SupportedLanguage.CPP: "tree_sitter_cpp",
    SupportedLanguage.C: "tree_sitter_c",
    SupportedLanguage.PHP: "tree_sitter_php",
    SupportedLanguage.RUBY: "tree_sitter_ruby",
    SupportedLanguage.KOTLIN: "tree_sitter_kotlin",
    SupportedLanguage.SWIFT: "tree_sitter_swift",
    SupportedLanguage.SCALA: "tree_sitter_scala",
    SupportedLanguage.DART: "tree_sitter_dart",
    SupportedLanguage.BASH: "tree_sitter_bash",
    SupportedLanguage.LUA: "tree_sitter_lua",
    SupportedLanguage.JSON: "tree_sitter_json",
    SupportedLanguage.TOML: "tree_sitter_toml",
    SupportedLanguage.YAML: "tree_sitter_yaml",
    SupportedLanguage.HTML: "tree_sitter_html",
    SupportedLanguage.CSS: "tree_sitter_css",
    SupportedLanguage.DOCKERFILE: "tree_sitter_dockerfile",
}


# Global parser instance
_treesitter_parser: Optional[TreeSitterParser] = None


def get_treesitter_parser() -> TreeSitterParser:
    """Get global Tree-sitter parser instance."""
    global _treesitter_parser
    if _treesitter_parser is None:
        _treesitter_parser = TreeSitterParser()
    return _treesitter_parser


def detect_language(file_path: str) -> Optional[SupportedLanguage]:
    """Detect language from file extension or name."""
    path = Path(file_path)
    
    # Check special filenames first
    if path.name in FILENAME_TO_LANGUAGE:
        return FILENAME_TO_LANGUAGE[path.name]
    
    # Check extensions
    for suffix in path.suffixes:
        if suffix.lower() in EXTENSION_TO_LANGUAGE:
            return EXTENSION_TO_LANGUAGE[suffix.lower()]
    
    # Check last suffix
    if path.suffix.lower() in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[path.suffix.lower()]
    
    return None