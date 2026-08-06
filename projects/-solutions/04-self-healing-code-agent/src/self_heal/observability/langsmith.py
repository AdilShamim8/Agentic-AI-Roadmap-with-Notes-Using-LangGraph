"""LangSmith tracing bootstrap.

LangSmith is configured purely through environment variables — once
`LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set, the `langchain_core`
tracing hooks pick them up automatically. This module just makes the gating
explicit and idempotent, and exposes `is_enabled()` so other code can decide
whether to attach extra metadata.
"""

from __future__ import annotations

import os

from self_heal.config import get_settings
from self_heal.logging import get_logger

log = get_logger(__name__)

_BOOTSTRAPPED = False


def is_enabled() -> bool:
    """True if LangSmith tracing is configured and active."""
    return get_settings().has_langsmith()


def maybe_enable_tracing() -> None:
    """Set the env vars LangSmith reads, if a key is configured.

    Idempotent. Safe to call when no key is present (no-op).
    """
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    s = get_settings()
    if not s.has_langsmith():
        log.info("langsmith.disabled", reason="missing_key_or_tracing_off")
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = s.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = s.langsmith_project
    log.info("langsmith.enabled", project=s.langsmith_project)
    _BOOTSTRAPPED = True
