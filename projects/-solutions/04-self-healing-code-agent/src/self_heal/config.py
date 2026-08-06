"""Centralized settings for the self-healing code agent.

All configuration is read from environment variables (with optional `.env` file).
Nothing in the codebase reads `os.environ` directly except this module.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderName(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class Settings(BaseSettings):
    """Runtime settings, loaded from env / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── LLM ────────────────────────────────────────────────────
    llm_provider: LLMProviderName = LLMProviderName.MOCK
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096

    # ── Agent ──────────────────────────────────────────────────
    max_iterations: int = Field(3, alias="SELF_HEAL_MAX_ITERATIONS")
    log_level: str = Field("INFO", alias="SELF_HEAL_LOG_LEVEL")
    max_cost_usd: float = Field(2.0, alias="SELF_HEAL_MAX_COST_USD")

    # ── LangSmith ──────────────────────────────────────────────
    langsmith_api_key: str = ""
    langsmith_tracing: bool = False
    langsmith_project: str = "self-healing-code-agent"

    # ── GitHub ─────────────────────────────────────────────────
    github_token: str = ""
    github_repo: str = ""  # owner/name

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_provider(cls, v: str | LLMProviderName) -> LLMProviderName:
        if isinstance(v, LLMProviderName):
            return v
        return LLMProviderName(str(v).lower())

    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    def has_langsmith(self) -> bool:
        return bool(self.langsmith_api_key) and self.langsmith_tracing

    def has_github(self) -> bool:
        return bool(self.github_token) and bool(self.github_repo)


# Module-level singleton; importers should use `get_settings()`.
_settings: Settings | None = None


def get_settings(refresh: bool = False) -> Settings:
    """Return the cached Settings instance, loading it on first access."""
    global _settings
    if _settings is None or refresh:
        _settings = Settings()
    return _settings


# Cost tables (USD per 1M tokens). Update as pricing changes.
# Source: provider pricing pages, Aug 2025.
COST_TABLE_USD_PER_M: dict[str, dict[Literal["input", "output"], float]] = {
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
    "claude-haiku-3-5": {"input": 0.8, "output": 4.0},
    "mock": {"input": 0.0, "output": 0.0},
}


def cost_for_model(model: str, in_tokens: int, out_tokens: int) -> float:
    """Estimate USD cost for a single LLM call."""
    table = COST_TABLE_USD_PER_M.get(model, COST_TABLE_USD_PER_M["mock"])
    return (in_tokens / 1_000_000) * table["input"] + (out_tokens / 1_000_000) * table["output"]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "fixtures"
