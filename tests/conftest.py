"""
Global pytest configuration and fixtures for LendingBot tests.

This conftest.py provides:
- Custom pytest markers for test categorization
- Automatic integration test skipping
- Test collection modifications
"""

import os
import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers.

    This function is called at the start of the test run and registers
    custom markers that can be used to decorate tests.

    Markers:
    - unit: Fast, isolated tests with no external dependencies
    - integration: Slow tests that make real API calls
    - slow: Tests that take more than 1 second to run
    """
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slow, real API calls, require API keys)"
    )
    config.addinivalue_line("markers", "slow: Slow-running tests (take > 1 second)")


def pytest_collection_modifyitems(config, items):
    """Modify collected test items after collection.

    This function:
    1. Automatically marks tests in tests/integration/ as 'integration' and 'slow'
    2. Skips integration tests unless RUN_INTEGRATION_TESTS environment variable is set

    Args:
        config: Pytest config object
        items: List of collected test items
    """
    # Check if integration tests should run
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"

    for item in items:
        # Automatically mark integration tests based on directory location
        if "integration" in str(item.fspath):
            item.add_marker("integration")
            item.add_marker("slow")

        # Skip integration tests by default (unless enabled via environment variable)
        if item.get_closest_marker("integration") and not run_integration:
            item.add_marker(
                pytest.mark.skipif(
                    not run_integration,
                    reason="Integration tests skipped. Set RUN_INTEGRATION_TESTS=true to run.",
                )
            )


# Add src to Python path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
