"""Shared pytest fixtures."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
EVALS = ROOT / "evals"


@pytest.fixture(autouse=True)
def _add_src_to_path() -> None:
    for p in (str(SRC), str(EVALS)):
        if p not in sys.path:
            sys.path.insert(0, p)


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """An empty git-initialized repo in a temp dir."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


@pytest.fixture
def fixtures_dir() -> Path:
    return ROOT / "fixtures"


@pytest.fixture
def copy_fixture(fixtures_dir: Path, tmp_path: Path):
    """Return a callable that copies a fixture case into a temp dir."""

    def _copy(name: str) -> Path:
        src = fixtures_dir / name
        dst = tmp_path / name
        shutil.copytree(src, dst)
        return dst

    return _copy
