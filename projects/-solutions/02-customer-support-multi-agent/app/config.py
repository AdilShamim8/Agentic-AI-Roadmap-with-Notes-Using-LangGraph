"""
Centralized configuration. Reads from environment variables (and a local
`.env` file via python-dotenv, if present) and decides which LLM provider
to use.

Provider resolution order:
  1. Explicit `LLM_PROVIDER` env var ("anthropic" | "openai" | "mock")
  2. Auto-detect: ANTHROPIC_API_KEY present -> anthropic
                  OPENAI_API_KEY present    -> openai
                  otherwise                 -> mock (no LLM calls, deterministic
                                                templated responses; the whole
                                                app still runs end-to-end)
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # no-op if there's no .env file


def _get_provider() -> str:
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit in ("anthropic", "openai", "mock"):
        return explicit
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "mock"


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    anthropic_api_key: str | None
    anthropic_model: str
    openai_api_key: str | None
    openai_model: str
    app_env: str
    log_level: str


def get_settings() -> Settings:
    return Settings(
        llm_provider=_get_provider(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


settings = get_settings()
