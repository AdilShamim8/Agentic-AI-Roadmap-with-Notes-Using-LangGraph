"""Base classes for the evaluator framework.

Every evaluator inherits from `BaseEvaluator` and implements `evaluate`.
The contract is intentionally narrow — an evaluator sees the row, the
agent's output, and the agent's trajectory, and returns an `EvalResult`.

This is the *only* interface the runner depends on, so adding a new
evaluator is a one-file change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from eval.schemas import AgentOutput, DatasetRow, EvalResult, Trajectory


class BaseEvaluator(ABC):
    """Abstract base class for all evaluators.

    Subclasses MUST implement `evaluate`. They MAY override `name` to
    customize how they appear in reports.
    """

    #: Display name used in reports. Defaults to the class name.
    name: str = ""

    def __init__(self, **params: Any) -> None:
        self.params = params

    @abstractmethod
    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        """Run the evaluator on one row.

        Args:
            row: The golden dataset row.
            output: The agent's output for this row.
            trajectory: The agent's execution trajectory (may be None).

        Returns:
            An `EvalResult` with `passed`, `score`, optional `rationale`.
        """

    # ----- helpers --------------------------------------------------------

    @classmethod
    def display_name(cls) -> str:
        return cls.name or cls.__name__

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} params={self.params}>"


class EvaluatorRegistry:
    """A simple name → class registry.

    This lets the runner resolve evaluator specs from YAML into concrete
    classes without a hard dependency on a DI framework.
    """

    _registry: dict[str, type[BaseEvaluator]] = {}

    @classmethod
    def register(cls, name: str, evaluator_cls: type[BaseEvaluator]) -> None:
        if not issubclass(evaluator_cls, BaseEvaluator):
            raise TypeError(f"{evaluator_cls} must subclass BaseEvaluator")
        cls._registry[name] = evaluator_cls

    @classmethod
    def get(cls, name: str) -> type[BaseEvaluator]:
        try:
            return cls._registry[name]
        except KeyError as exc:
            available = ", ".join(sorted(cls._registry))
            raise KeyError(
                f"Unknown evaluator {name!r}. Available: {available}."
            ) from exc

    @classmethod
    def all_names(cls) -> list[str]:
        return sorted(cls._registry)

    @classmethod
    def build(cls, name: str, params: dict[str, Any] | None = None) -> BaseEvaluator:
        """Instantiate an evaluator by name with the given params."""

        evaluator_cls = cls.get(name)
        return evaluator_cls(**(params or {}))
