"""
OpenAI Chat Completions backend.

Uses the OpenAI Python SDK to call the Chat Completions API.  This backend
is activated when ``LLM_BACKEND=openai`` and ``OPENAI_API_KEY`` are set.

The ``openai`` package is imported lazily so that the project runs without
it installed when using the mock backend.
"""

from __future__ import annotations

import time
from typing import Any

from llm.base import LLMBackend, LLMResponse


class OpenAIBackend(LLMBackend):
    """LLM backend backed by the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        # Lazy import — avoids hard dependency on the openai package.
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAIBackend. "
                "Install it with: pip install openai"
            ) from exc

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model

    @property
    def name(self) -> str:
        return f"OpenAI({self._model})"

    @property
    def model_id(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        t0 = time.perf_counter()
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        choice = response.choices[0]
        text = choice.message.content or ""
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            text=text,
            model=response.model,
            usage=usage,
            latency_ms=elapsed_ms,
            metadata={"backend": "openai", "finish_reason": choice.finish_reason},
        )
