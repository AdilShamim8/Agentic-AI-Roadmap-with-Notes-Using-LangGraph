"""Environment / .env configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    llm_provider: str
    llm_model: str | None
    max_results_per_query: int
    max_iterations: int
    use_langgraph: bool


def load_settings() -> Settings:
    """Load `.env` (if present) and return resolved settings."""

    load_dotenv()

    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "anthropic").lower(),
        llm_model=os.getenv("LLM_MODEL") or None,
        max_results_per_query=int(os.getenv("MAX_RESULTS_PER_QUERY", "4")),
        max_iterations=int(os.getenv("MAX_ITERATIONS", "2")),
        use_langgraph=os.getenv("USE_LANGGRAPH", "true").lower() not in ("0", "false", "no"),
    )
