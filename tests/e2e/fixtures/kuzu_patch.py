"""Test-specific patch for KuzuGraphStore to read KUZU_DB_PATH from environment."""

import os
import sys

# Ensure project root is in path for devlensx imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# This must be imported BEFORE any devlensx modules that use KuzuGraphStore
# It patches KuzuGraphStore to use the KUZU_DB_PATH environment variable

_original_init = None


def _patched_init(self, db_path="devlensx_graph_db"):
    """Patched init that reads KUZU_DB_PATH from environment."""
    env_path = os.environ.get("KUZU_DB_PATH")
    if env_path:
        db_path = env_path
    return _original_init(self, db_path)


def apply_kuzu_patch():
    """Apply the KuzuGraphStore patch to use KUZU_DB_PATH env var."""
    global _original_init
    from devlensx.graph.kuzu_store import KuzuGraphStore
    if _original_init is None:
        _original_init = KuzuGraphStore.__init__
        KuzuGraphStore.__init__ = _patched_init


# Apply patch immediately when this module is imported
apply_kuzu_patch()