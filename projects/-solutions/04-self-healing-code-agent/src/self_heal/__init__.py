"""Self-healing code agent.

A LangGraph-based agent that reproduces a failing test, diagnoses the cause,
writes a patch, verifies it, and iterates with reflexion until the test passes
or a max-iteration limit is hit.
"""

from __future__ import annotations

__version__ = "0.1.0"

from self_heal.config import Settings, get_settings

__all__ = ["Settings", "__version__", "get_settings"]
