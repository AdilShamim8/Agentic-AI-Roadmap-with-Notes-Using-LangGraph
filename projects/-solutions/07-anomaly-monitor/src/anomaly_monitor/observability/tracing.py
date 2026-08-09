"""LangSmith tracing setup.

``configure_tracing(settings)`` sets the ``LANGSMITH_TRACING`` /
``LANGSMITH_API_KEY`` / ``LANGSMITH_PROJECT`` env vars when LangSmith is
enabled, so that langchain's tracing subsystem picks them up at import time.
It MUST be called BEFORE langchain is imported; the function is idempotent
so repeat calls are safe.

``@traced(name)`` wraps a function with
``langchain_core.tracers.context.tracing_v2_enabled()`` (preferred, langchain
0.2.x+) or ``tracing_enabled()`` (older versions) if LangSmith is configured,
otherwise it returns the function unchanged (true no-op, zero runtime
overhead). The langchain_core import is done lazily inside the wrapper so
module load does not depend on langchain being installed.

The ``name`` parameter is metadata used for structlog logging when
langchain_core is unavailable; the tracing context manager itself is invoked
with no args so that the project/session configured via ``LANGSMITH_PROJECT``
is honoured (overriding it would split traces across per-function projects).
"""

from __future__ import annotations

import functools
import inspect
import os
from typing import Any, Callable, Optional, TypeVar

import structlog

from anomaly_monitor.config import Settings

log = structlog.get_logger()

_CONFIGURED: bool = False


def configure_tracing(settings: Settings) -> None:
    """Set ``LANGSMITH_*`` env vars if enabled, otherwise no-op.

    Idempotent: subsequent calls are no-ops. Must be called BEFORE langchain
    is imported so the tracing subsystem picks up the env vars.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    if not settings.langsmith_enabled:
        log.debug("langsmith_tracing_disabled")
        return
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    _CONFIGURED = True
    log.info(
        "langsmith_tracing_configured", project=settings.langsmith_project
    )


def _get_tracing_cm(label: str) -> Optional[Any]:
    """Construct a langchain tracing context manager.

    Tries ``tracing_v2_enabled`` first (langchain_core 0.2.x+); falls back to
    ``tracing_enabled`` for older versions. Returns ``None`` if langchain_core
    is unavailable or the context manager cannot be constructed (e.g. the
    v1 API raises ``RuntimeError`` because it has been deprecated).
    """
    try:
        from langchain_core.tracers.context import tracing_v2_enabled as _fn
    except ImportError:
        try:
            from langchain_core.tracers.context import (
                tracing_enabled as _fn,
            )
        except ImportError:
            log.warning(
                "langchain_core_unavailable_tracing_skipped",
                function=label,
            )
            return None
    try:
        # No args: use the default project set via LANGSMITH_PROJECT env var.
        return _fn()
    except Exception as e:  # pragma: no cover - defensive
        log.warning(
            "tracing_context_unavailable_skipping",
            function=label,
            error=str(e),
        )
        return None


F = TypeVar("F", bound=Callable[..., Any])


def traced(name: str | None = None) -> Callable[[F], F]:
    """Decorator: wrap a function with a langchain tracing context manager.

    If LangSmith is not configured at decoration time, returns the function
    unchanged (true no-op, zero overhead). The ``langchain_core`` import is
    done lazily inside the wrapper so module load does not depend on langchain.
    """

    def decorator(func: F) -> F:
        if not _CONFIGURED:
            return func  # true no-op passthrough

        label = name or func.__name__

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                cm = _get_tracing_cm(label)
                if cm is None:
                    return await func(*args, **kwargs)
                # `tracing_v2_enabled` returns a SYNC context manager; entering
                # and exiting it only touches context vars (no I/O), so it is
                # safe to use `with` inside an async function.
                with cm:
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            cm = _get_tracing_cm(label)
            if cm is None:
                return func(*args, **kwargs)
            with cm:
                return func(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator
