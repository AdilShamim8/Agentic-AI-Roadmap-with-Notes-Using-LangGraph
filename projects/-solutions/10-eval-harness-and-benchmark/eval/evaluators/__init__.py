"""Evaluator package.

Exposes a registry so the runner can resolve evaluator names from the
YAML spec into concrete classes.
"""

from eval.evaluators.base import BaseEvaluator, EvaluatorRegistry
from eval.evaluators.rule_based import (
    ExactMatchEvaluator,
    ContainsEvaluator,
    RegexMatchEvaluator,
    NumericCloseEvaluator,
    JsonFieldMatchEvaluator,
)
from eval.evaluators.llm_judge import LLMJudgeEvaluator
from eval.evaluators.trajectory import TrajectoryMatchEvaluator

__all__ = [
    "BaseEvaluator",
    "EvaluatorRegistry",
    "ExactMatchEvaluator",
    "ContainsEvaluator",
    "RegexMatchEvaluator",
    "NumericCloseEvaluator",
    "JsonFieldMatchEvaluator",
    "LLMJudgeEvaluator",
    "TrajectoryMatchEvaluator",
]


# Register the built-in evaluators on the default registry.
EvaluatorRegistry.register("exact_match", ExactMatchEvaluator)
EvaluatorRegistry.register("contains", ContainsEvaluator)
EvaluatorRegistry.register("regex_match", RegexMatchEvaluator)
EvaluatorRegistry.register("numeric_close", NumericCloseEvaluator)
EvaluatorRegistry.register("json_field_match", JsonFieldMatchEvaluator)
EvaluatorRegistry.register("llm_judge", LLMJudgeEvaluator)
EvaluatorRegistry.register("trajectory_match", TrajectoryMatchEvaluator)
