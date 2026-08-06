"""LLM provider base types and factory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from self_heal.config import Settings, get_settings
from self_heal.logging import get_logger

log = get_logger(__name__)


@dataclass
class Message:
    """A single chat message."""

    role: Literal["system", "user", "assistant"]
    content: str
    name: str | None = None


@dataclass
class TokenUsage:
    """Token accounting for a single completion."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LLMResponse:
    """The result of a single `complete` call."""

    content: str
    usage: TokenUsage
    model: str
    raw: dict | None = None  # provider-specific raw payload, for debugging


@runtime_checkable
class LLMProvider(Protocol):
    """What the agent expects from an LLM backend."""

    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def complete(self, messages: list[Message]) -> LLMResponse: ...


def provider_factory(settings: Settings | None = None) -> LLMProvider:
    """Build the configured LLM provider.

    Selection order:
      1. If `settings.llm_provider == mock` → MockProvider.
      2. If openai and the key is present → OpenAIProvider.
      3. If anthropic and the key is present → AnthropicProvider.
      4. Otherwise fall back to MockProvider with a warning.

    This makes the whole agent runnable with zero API keys (useful for the
    fixture smoke-tests and CI).
    """
    s = settings or get_settings()

    if s.llm_provider.value == "mock":
        log.info("llm.provider.selected", provider="mock")
        from self_heal.llm.mock import MockProvider

        return MockProvider()

    if s.llm_provider.value == "openai":
        if not s.has_openai():
            log.warning(
                "llm.provider.missing_key",
                provider="openai",
                fallback="mock",
            )
            from self_heal.llm.mock import MockProvider

            return MockProvider()
        from self_heal.llm.openai_provider import OpenAIProvider

        log.info("llm.provider.selected", provider="openai", model=s.openai_model)
        return OpenAIProvider(s)

    if s.llm_provider.value == "anthropic":
        if not s.has_anthropic():
            log.warning(
                "llm.provider.missing_key",
                provider="anthropic",
                fallback="mock",
            )
            from self_heal.llm.mock import MockProvider

            return MockProvider()
        from self_heal.llm.anthropic_provider import AnthropicProvider

        log.info("llm.provider.selected", provider="anthropic", model=s.anthropic_model)
        return AnthropicProvider(s)

    # Unknown provider — fall back to mock.
    log.warning("llm.provider.unknown", requested=s.llm_provider, fallback="mock")
    from self_heal.llm.mock import MockProvider

    return MockProvider()
