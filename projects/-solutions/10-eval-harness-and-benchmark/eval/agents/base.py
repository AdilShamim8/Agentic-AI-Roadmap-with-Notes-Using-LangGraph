"""Base class for agents.

The harness is *agent-framework-agnostic*: it does not care whether your
agent is built with LangGraph, OpenAI Agents SDK, CrewAI, or plain
Python. As long as you can wrap it in a `BaseAgent`, the runner can
evaluate it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from eval.schemas import AgentOutput, Trajectory


class BaseAgent(ABC):
    """Abstract base class for agents.

    Subclasses MUST implement `run(input) -> AgentOutput`. They MAY
    override `__init__` to take config, but should call `super().__init__()`.
    """

    #: Human-readable name shown in reports.
    name: str = "BaseAgent"

    #: The pattern this agent implements (e.g. "react"). Used by the
    #: registry to suggest sensible defaults, but the runner never reads it.
    pattern: str = "unknown"

    def __init__(self, **kwargs) -> None:
        self.config = kwargs

    @abstractmethod
    def run(self, input: str) -> AgentOutput:
        """Run the agent on a single input.

        Args:
            input: The user's input / task string.

        Returns:
            An `AgentOutput` with at least `.answer` populated. The
            `.trajectory` field is optional but recommended — trajectory
            evaluators cannot run without it.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} pattern={self.pattern!r}>"


# Re-export schema types that agents need.
__all__ = ["BaseAgent", "AgentOutput", "Trajectory"]
