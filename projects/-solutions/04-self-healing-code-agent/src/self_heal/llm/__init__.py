"""LLM provider abstraction.

A single `LLMProvider` protocol that the agent talks to. Concrete implementations:
- OpenAIProvider  (openai SDK, GPT-4o family)
- AnthropicProvider (anthropic SDK, Claude Sonnet family)
- MockProvider    (deterministic, no network — used in tests and dry-runs)
"""

from __future__ import annotations

from self_heal.llm.base import (
    LLMProvider,
    Message,
    TokenUsage,
    provider_factory,
)
from self_heal.llm.mock import MockProvider

__all__ = [
    "LLMProvider",
    "Message",
    "MockProvider",
    "TokenUsage",
    "provider_factory",
]
