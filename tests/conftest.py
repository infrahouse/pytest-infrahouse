import logging

import pytest

pytest_plugins = "pytester"

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

LOG = logging.getLogger(__name__)


# Pytest hooks
# More details on
# https://pytest-with-eric.com/hooks/pytest-hooks/#Test-Running-runtest-Hooks
def pytest_runtest_logstart(nodeid, location):
    """Log when a test starts."""
    LOG.info(f"TEST STARTED: {nodeid}")


def pytest_runtest_logfinish(nodeid, location):
    """Log when a test finishes."""
    LOG.info(f"TEST ENDED: {nodeid}")
