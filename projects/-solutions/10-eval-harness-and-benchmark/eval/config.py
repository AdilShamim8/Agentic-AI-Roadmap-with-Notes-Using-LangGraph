"""Env-driven configuration for the eval harness.

All config is read from environment variables (with sane defaults) so the
harness is fully usable without an `.env` file. Loading `.env` is the
caller's responsibility (the CLI does it in `cli.py`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the harness config.

    Frozen so it is safe to pass around between threads / processes during
    parallel runs.
    """

    llm_provider: str = field(default_factory=lambda: _env("EVAL_LLM_PROVIDER", "mock"))
    openai_api_key: str | None = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY")
    )
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o"))
    anthropic_api_key: str | None = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY")
    )
    anthropic_model: str = field(
        default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    )
    llm_temperature: float = field(
        default_factory=lambda: _env_float("EVAL_LLM_TEMPERATURE", 0.0)
    )

    run_timeout_s: int = field(default_factory=lambda: _env_int("EVAL_RUN_TIMEOUT", 60))
    workers: int = field(default_factory=lambda: _env_int("EVAL_WORKERS", 1))
    seed: int = field(default_factory=lambda: _env_int("EVAL_SEED", 42))

    report_dir: Path = field(
        default_factory=lambda: Path(_env("EVAL_REPORT_DIR", "reports"))
    )

    # Root of the harness (where benchmarks/ lives). Defaults to cwd.
    project_root: Path = field(default_factory=lambda: Path(_env("EVAL_PROJECT_ROOT", ".")))

    @property
    def benchmarks_dir(self) -> Path:
        return self.project_root / "benchmarks"

    @property
    def datasets_dir(self) -> Path:
        return self.benchmarks_dir / "datasets"

    @property
    def trajectories_dir(self) -> Path:
        return self.benchmarks_dir / "trajectories"

    @property
    def baselines_dir(self) -> Path:
        return self.benchmarks_dir / "baselines"

    @property
    def registry_path(self) -> Path:
        return self.benchmarks_dir / "registry.yaml"


def get_settings() -> Settings:
    """Return a fresh snapshot of settings.

    We re-read on every call so that tests that mutate env vars are picked
    up. The result is frozen, so callers cannot accidentally mutate it.
    """

    return Settings()


def ensure_dirs(settings: Settings) -> None:
    """Create the report dir if missing. Other dirs are read-only by default."""

    settings.report_dir.mkdir(parents=True, exist_ok=True)
