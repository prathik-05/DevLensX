"""
DevLensX Adapter Registry Initialization
Registers all language adapters into a single shared registry.
"""

from typing import Optional

from devlensx.urm.adapters.base import AdapterRegistry, get_adapter_registry as _base_get_registry

_registry: Optional[AdapterRegistry] = None


def _register_all_adapters(registry: AdapterRegistry):
    """Register all language adapters. Imported lazily to avoid circular imports."""
    from devlensx.urm.adapters.java_adapter import JavaLanguageAdapter
    from devlensx.urm.adapters.python_adapter import PythonLanguageAdapter
    from devlensx.urm.adapters.typescript_adapter import TypeScriptLanguageAdapter
    from devlensx.urm.adapters.go_adapter import GoLanguageAdapter
    from devlensx.urm.adapters.rust_adapter import RustLanguageAdapter
    from devlensx.urm.adapters.csharp_adapter import CSharpLanguageAdapter
    from devlensx.urm.adapters.cpp_adapter import CppLanguageAdapter

    registry.register(JavaLanguageAdapter())
    registry.register(PythonLanguageAdapter())
    registry.register(TypeScriptLanguageAdapter())
    registry.register(GoLanguageAdapter())
    registry.register(RustLanguageAdapter())
    registry.register(CSharpLanguageAdapter())
    registry.register(CppLanguageAdapter())


def get_initialized_registry() -> AdapterRegistry:
    """Get or create the initialized adapter registry."""
    global _registry
    if _registry is None:
        _registry = _base_get_registry()
        _register_all_adapters(_registry)
    return _registry


def initialize_adapters() -> AdapterRegistry:
    """Initialize and register all language adapters (public API)."""
    return get_initialized_registry()


# Backward-compatible alias
def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry, initializing all adapters on first call."""
    return get_initialized_registry()


__all__ = [
    "get_initialized_registry",
    "initialize_adapters",
    "get_adapter_registry",
    "AdapterRegistry",
]