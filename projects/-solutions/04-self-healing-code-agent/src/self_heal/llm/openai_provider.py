"""OpenAI Chat Completions provider."""

from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

from self_heal.config import Settings, cost_for_model
from self_heal.llm.base import LLMResponse, Message, TokenUsage
from self_heal.logging import get_logger

log = get_logger(__name__)


class OpenAIProvider:
    """Thin wrapper over the OpenAI Python SDK."""

    name = "openai"

    def __init__(self, settings: Settings) -> None:
        from openai import OpenAI  # imported lazily so the dep is optional

        self._settings = settings
        self._model = settings.openai_model
        self._client = OpenAI(api_key=settings.openai_api_key)

    @property
    def model(self) -> str:
        return self._model

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1.5, min=2, max=20),
    )
    def complete(self, messages: list[Message]) -> LLMResponse:
        payload = [
            {"role": m.role, "content": m.content, **({"name": m.name} if m.name else {})}
            for m in messages
        ]
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=payload,  # type: ignore[arg-type]
            temperature=self._settings.llm_temperature,
            max_tokens=self._settings.llm_max_tokens,
        )

        choice = resp.choices[0]
        content = choice.message.content or ""
        usage = TokenUsage(
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )
        cost = cost_for_model(self._model, usage.input_tokens, usage.output_tokens)
        log.debug(
            "llm.openai.complete",
            model=self._model,
            in_tokens=usage.input_tokens,
            out_tokens=usage.output_tokens,
            cost_usd=round(cost, 6),
        )
        return LLMResponse(
            content=content,
            usage=usage,
            model=self._model,
            raw=resp.model_dump() if hasattr(resp, "model_dump") else None,
        )
