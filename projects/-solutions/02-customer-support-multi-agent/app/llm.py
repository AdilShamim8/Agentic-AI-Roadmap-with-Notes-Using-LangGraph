"""
LLM factory. Returns a LangChain chat model instance for whichever provider
is configured, or `None` if we're in "mock" mode (no API key configured).

Every agent node checks `get_llm()` and falls back to a deterministic,
template-based response when it returns None - so the entire graph runs
end-to-end with zero API keys and zero cost, which is handy for local
development, CI, and grading/demoing this project without paying for
tokens. Add a real key in `.env` to get natural-language, tool-calling
agents powered by Claude or GPT.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def get_llm():
    """Return a cached chat model instance, or None for mock mode."""
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model,
            temperature=0.2,
            api_key=settings.anthropic_api_key,
        )

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            temperature=0.2,
            api_key=settings.openai_api_key,
        )

    return None  # mock mode


def is_mock_mode() -> bool:
    return settings.llm_provider == "mock"
