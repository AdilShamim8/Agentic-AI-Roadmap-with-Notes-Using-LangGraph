"""Pytest fixtures shared across the test suite.

Each test run uses a fresh temp DATA_DIR so ChromaDB / SQLite state
never leaks between runs.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def samples_dir() -> Path:
    """Absolute path to the bundled samples/ directory."""
    return Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture(scope="session", autouse=True)
def _ensure_samples(samples_dir: Path) -> None:
    """Generate sample PDFs once per session if they don't exist."""
    if not (samples_dir / "financial_report.pdf").exists():
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "scripts" / "generate_samples.py")],
            check=True,
            cwd=str(samples_dir.parent),
        )


@pytest.fixture(autouse=True)
def _temp_data_dir(monkeypatch, tmp_path):
    """Redirect DATA_DIR to a per-test temp dir."""
    tmp = tmp_path / "data"
    tmp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATA_DIR", str(tmp))
    # Force settings to refresh.
    from doc_analyst import config as cfg

    cfg.settings = cfg.Settings()
    cfg.settings.ensure_dirs()

    # Reset singletons so they pick up the new DATA_DIR.
    from doc_analyst.storage import vector_store, doc_registry

    vector_store.reset_store()
    doc_registry.reset_registry()

    yield

    vector_store.reset_store()
    doc_registry.reset_registry()
    shutil.rmtree(tmp, ignore_errors=True)
