"""Test backend entry point with Kuzu patch applied."""

import os
import sys
import importlib.util

# Add project root to path FIRST
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
print(f"[test_backend] Added to sys.path: {project_root}", flush=True)
print(f"[test_backend] sys.path[0]: {sys.path[0]}", flush=True)

# Apply Kuzu patch BEFORE importing any devlensx modules
# Use direct file import to avoid package resolution issues
fixtures_dir = os.path.dirname(os.path.abspath(__file__))
kuzu_patch_path = os.path.join(fixtures_dir, "kuzu_patch.py")

spec = importlib.util.spec_from_file_location("kuzu_patch", kuzu_patch_path)
kuzu_patch_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kuzu_patch_module)
kuzu_patch_module.apply_kuzu_patch()

# Now import and run the app
import uvicorn
from devlensx.api.main import app

if __name__ == "__main__":
    port = int(os.environ.get("DEVLENSX_BACKEND_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, access_log=False)