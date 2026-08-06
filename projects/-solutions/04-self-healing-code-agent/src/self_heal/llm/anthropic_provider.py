"""Anthropic Messages API provider."""

from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

from self_heal.config import Settings, cost_for_model
from self_heal.llm.base import LLMResponse, Message, TokenUsage
from self_heal.logging import get_logger

log = get_logger(__name__)


class AnthropicProvider:
    """Thin wrapper over the Anthropic Python SDK."""

    name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        from anthropic import Anthropic  # imported lazily

        self._settings = settings
        self._model = settings.anthropic_model
        self._client = Anthropic(api_key=settings.anthropic_api_key)

    @property
    def model(self) -> str:
        return self._model

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1.5, min=2, max=20),
    )
    def complete(self, messages: list[Message]) -> LLMResponse:
        # Anthropic splits system message from the conversation.
        sys_msgs = [m.content for m in messages if m.role == "system"]
        convo = [
            {"role": ("user" if m.role == "user" else "assistant"), "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        system = "\n\n".join(sys_msgs) if sys_msgs else None

        kwargs: dict = {
            "model": self._model,
            "messages": convo,
            "max_tokens": self._settings.llm_max_tokens,
            "temperature": self._settings.llm_temperature,
        }
        if system:
            kwargs["system"] = system

        resp = self._client.messages.create(**kwargs)

        content = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        usage = TokenUsage(
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
        cost = cost_for_model(self._model, usage.input_tokens, usage.output_tokens)
        log.debug(
            "llm.anthropic.complete",
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
