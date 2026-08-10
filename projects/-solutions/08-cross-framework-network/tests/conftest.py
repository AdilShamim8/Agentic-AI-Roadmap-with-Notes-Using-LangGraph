"""Pytest configuration — shared fixtures and path setup."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Ensure the project root is on sys.path so `import a2a`, `import agents`, etc. work
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def anyio_backend():
    return "asyncio"
