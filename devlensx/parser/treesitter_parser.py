"""
DevLensX Tree-sitter Polyglot Parser Foundation
Provides unified parsing across all supported languages using Tree-sitter.
"""

from devlensx.shared.types import (
    TreeSitterParser,
    get_treesitter_parser,
    ParseResult,
    SupportedLanguage,
    detect_language,
    EXTENSION_TO_LANGUAGE,
    FILENAME_TO_LANGUAGE,
    TS_LANGUAGE_MODULES,
)