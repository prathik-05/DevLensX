"""E2E test configuration with isolated fixtures."""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Ensure test isolation by not sharing state between tests
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest for E2E tests."""
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end (requires isolated environment)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (takes > 30s)"
    )


def pytest_collection_modifyitems(config, items):
    """Add markers to E2E tests."""
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)


# Import fixtures using relative import
from tests.e2e.fixtures.server import isolated_env, petclinic_analysis, battleship_analysis

__all__ = ["isolated_env", "petclinic_analysis", "battleship_analysis"]