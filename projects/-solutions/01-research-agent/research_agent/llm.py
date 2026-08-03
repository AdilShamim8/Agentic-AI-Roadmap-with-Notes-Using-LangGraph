"""LLM provider adapters.

Every adapter exposes the same tiny interface:

    generate(prompt: str, system: str | None = None) -> str

That's the only thing the rest of the agent depends on, which keeps
`nodes.py` completely provider-agnostic and trivially testable with
`FakeLLM` (no network, no API key, no LangChain dependency required).
"""

from __future__ import annotations

import os
from typing import Callable, Optional, Protocol


class LLMClient(Protocol):
    def generate(self, prompt: str, system: Optional[str] = None) -> str: ...


class OpenAIClient:
    """Adapter around the official `openai` SDK."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None, temperature: float = 0.2):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "The 'openai' package is required for OpenAIClient. "
                "Install it with: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""


class AnthropicClient:
    """Adapter around the official `anthropic` SDK."""

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: Optional[str] = None, temperature: float = 0.2):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "The 'anthropic' package is required for AnthropicClient. "
                "Install it with: pip install anthropic"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
        self.temperature = temperature

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=self.temperature,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        return "".join(parts)


class OllamaClient:
    """Adapter around a local Ollama server — no API key needed."""

    def __init__(self, model: str = "llama3.1", host: Optional[str] = None, temperature: float = 0.2):
        self.model = model
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.temperature = temperature

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        import requests

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json().get("response", "")


class FakeLLM:
    """Deterministic, offline stand-in for tests and demos.

    `responder` is a function `(prompt, system) -> str` that lets tests
    return different canned text depending on which step of the pipeline
    is calling. If not given, a generic default responder is used.
    """

    def __init__(self, responder: Optional[Callable[[str, Optional[str]], str]] = None):
        self.responder = responder or (lambda prompt, system: "")
        self.calls = []

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        self.calls.append({"prompt": prompt, "system": system})
        return self.responder(prompt, system)


def build_llm(provider: str, model: Optional[str] = None) -> LLMClient:
    """Explicit factory — build a client for a given provider name."""

    provider = provider.lower()
    if provider == "openai":
        return OpenAIClient(model=model or "gpt-4o-mini")
    if provider == "ollama":
        return OllamaClient(model=model or "llama3.1")
    if provider == "anthropic":
        return AnthropicClient(model=model or "claude-sonnet-4-6")

    raise ValueError(f"Unknown LLM provider '{provider}'. Use openai, anthropic, or ollama.")


def build_llm_from_env() -> LLMClient:
    """Factory that picks a provider based on environment variables.

    LLM_PROVIDER=openai|anthropic|ollama (default: anthropic)
    LLM_MODEL=<model name>          (provider-specific default if unset)
    """

    provider = os.getenv("LLM_PROVIDER", "anthropic")
    model = os.getenv("LLM_MODEL")
    return build_llm(provider, model)
