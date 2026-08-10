"""
Abstract LLM backend interface.

Every backend (mock, OpenAI, Anthropic, local, ...) implements this
interface so that agents can be framework-agnostic with respect to the
underlying model.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """A response from an LLM backend."""

    text: str
    model: str = "unknown"
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMBackend(ABC):
    """Abstract base class for all LLM backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this backend."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Model identifier (e.g. 'gpt-4o', 'mock-default')."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a text completion for the given prompt."""


def get_llm() -> LLMBackend:
    """
    Factory: return the LLM backend configured via environment variables.

    Selection logic:
        1. If ``LLM_BACKEND`` is ``"openai"`` and ``OPENAI_API_KEY`` is set,
           return :class:`OpenAIBackend`.
        2. Otherwise return :class:`MockLLM`.

    This is called lazily so that tests and services can override the
    environment between runs.
    """
    backend = os.environ.get("LLM_BACKEND", "mock").lower().strip()

    if backend == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            # Import here to avoid a hard dependency on the openai package.
            from llm.openai_backend import OpenAIBackend

            model = os.environ.get("OPENAI_MODEL", "gpt-4o")
            return OpenAIBackend(api_key=api_key, model=model)
        else:
            import warnings

            warnings.warn(
                "LLM_BACKEND=openai but OPENAI_API_KEY is not set; "
                "falling back to MockLLM.",
                stacklevel=2,
            )

    from llm.mock import MockLLM

    return MockLLM(
        persona=os.environ.get("MOCK_LLM_PERSONA", "general"),
        model_id=os.environ.get("MOCK_LLM_MODEL", "mock-default"),
    )
