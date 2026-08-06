"""Observability integration (LangSmith, env-gated)."""

from self_heal.observability.langsmith import (
    is_enabled,
    maybe_enable_tracing,
)

__all__ = ["is_enabled", "maybe_enable_tracing"]
