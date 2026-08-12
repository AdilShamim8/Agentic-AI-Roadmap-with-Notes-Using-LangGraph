"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Make sure the eval package is importable.
sys.path.insert(0, str(ROOT))

# Force a deterministic config for all tests.
os.environ.setdefault("EVAL_LLM_PROVIDER", "mock")
os.environ.setdefault("EVAL_SEED", "42")
os.environ.setdefault("EVAL_PROJECT_ROOT", str(ROOT))


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def datasets_dir(project_root: Path) -> Path:
    return project_root / "benchmarks" / "datasets"


@pytest.fixture(scope="session")
def trajectories_dir(project_root: Path) -> Path:
    return project_root / "benchmarks" / "trajectories"
