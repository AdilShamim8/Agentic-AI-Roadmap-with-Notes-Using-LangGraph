"""Rule-based evaluators.

These are fast, deterministic, and have zero API cost. They are the
backbone of any eval suite — use them wherever a string/numeric/JSON
comparison is possible, and reserve LLM-as-judge for cases that genuinely
need semantic judgement.
"""

from __future__ import annotations

import json
import re
from typing import Any

from eval.evaluators.base import BaseEvaluator
from eval.schemas import AgentOutput, DatasetRow, EvalResult, Trajectory
from eval.utils import answer_to_str, normalize_answer


class ExactMatchEvaluator(BaseEvaluator):
    """Pass iff the agent's answer (normalised) equals the expected answer.

    Honours `expected.allowed_answers` if present (any match counts).
    """

    name = "exact_match"

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        got = normalize_answer(answer_to_str(output.answer))
        candidates: list[str] = []
        if row.expected.answer is not None:
            candidates.append(normalize_answer(answer_to_str(row.expected.answer)))
        if row.expected.allowed_answers:
            candidates.extend(
                normalize_answer(answer_to_str(a)) for a in row.expected.allowed_answers
            )

        passed = got in candidates if candidates else False
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=passed,
            score=1.0 if passed else 0.0,
            rationale=(
                f"Exact match against {len(candidates)} candidate(s)."
                if passed
                else f"No exact match. Got: {got[:120]!r}."
            ),
            details={"got": got, "candidates": candidates},
        )


class ContainsEvaluator(BaseEvaluator):
    """Pass iff the answer contains all `must_contain` substrings and none
    of `must_not_contain`.

    Score = fraction of `must_contain` items present (1.0 if list is empty
    and the `must_not_contain` constraint holds).
    """

    name = "contains"

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        text = answer_to_str(output.answer)
        text_norm = text.lower()

        must_contain = row.expected.must_contain or []
        must_not_contain = row.expected.must_not_contain or []

        present = [s for s in must_contain if s.lower() in text_norm]
        forbidden_present = [s for s in must_not_contain if s.lower() in text_norm]

        if must_contain:
            score = len(present) / len(must_contain)
        else:
            score = 1.0 if not forbidden_present else 0.0

        # If any forbidden substring is present, force fail.
        if forbidden_present:
            score = 0.0

        passed = score == 1.0
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=passed,
            score=score,
            rationale=(
                f"Contained {len(present)}/{len(must_contain)} required; "
                f"forbidden hits: {len(forbidden_present)}."
            ),
            details={
                "missing": [s for s in must_contain if s not in present],
                "forbidden_hits": forbidden_present,
            },
        )


class RegexMatchEvaluator(BaseEvaluator):
    """Pass iff the answer matches `expected.regex`."""

    name = "regex_match"

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        pattern = row.expected.regex
        if not pattern:
            return EvalResult(
                evaluator=self.display_name(),
                row_id=row.id,
                passed=False,
                score=0.0,
                rationale="No regex configured for this row.",
            )
        text = answer_to_str(output.answer)
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        passed = m is not None
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=passed,
            score=1.0 if passed else 0.0,
            rationale=("Matched." if passed else "No match."),
            details={"regex": pattern, "match": m.group(0) if m else None},
        )


class NumericCloseEvaluator(BaseEvaluator):
    """Pass iff the agent's answer, parsed as a number, is within tolerance
    of `expected.numeric_value`.

    The first number found in the answer string is used; if none is found,
    the evaluator fails with score 0.0.
    """

    name = "numeric_close"

    _NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        target = row.expected.numeric_value
        tol = row.expected.numeric_tolerance
        if target is None:
            return EvalResult(
                evaluator=self.display_name(),
                row_id=row.id,
                passed=False,
                score=0.0,
                rationale="No numeric_value set on row.",
            )

        text = answer_to_str(output.answer)
        m = self._NUM_RE.search(text)
        if not m:
            return EvalResult(
                evaluator=self.display_name(),
                row_id=row.id,
                passed=False,
                score=0.0,
                rationale=f"No number found in answer: {text[:120]!r}",
            )
        try:
            got = float(m.group(0))
        except ValueError:
            got = float("nan")

        diff = abs(got - target)
        passed = diff <= tol
        # Smooth score: 1.0 at diff=0, 0.0 at diff=tol*4.
        score = max(0.0, 1.0 - diff / (tol * 4 if tol else 1.0))
        if not passed:
            score = min(score, 0.49)
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=passed,
            score=score,
            rationale=(
                f"Got {got}, target {target} ± {tol}. Δ={diff:.4g}."
            ),
            details={"got": got, "target": target, "tol": tol, "diff": diff},
        )


class JsonFieldMatchEvaluator(BaseEvaluator):
    """Pass iff a specific field in the agent's JSON answer matches.

    Params:
        field: dotted path into the JSON (e.g. "user.name" or "items.0.id").
        equals: the expected value (string compare after normalisation).
    """

    name = "json_field_match"

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        field = self.params.get("field") or row.expected.__dict__.get("field")
        expected_val = self.params.get("equals")

        answer = output.answer
        if isinstance(answer, str):
            try:
                answer = json.loads(answer)
            except json.JSONDecodeError:
                return EvalResult(
                    evaluator=self.display_name(),
                    row_id=row.id,
                    passed=False,
                    score=0.0,
                    rationale="Answer is not valid JSON.",
                )

        if field is None:
            return EvalResult(
                evaluator=self.display_name(),
                row_id=row.id,
                passed=False,
                score=0.0,
                rationale="No 'field' configured for json_field_match.",
            )

        got = _dig(answer, field)
        passed = _eq(got, expected_val)
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=passed,
            score=1.0 if passed else 0.0,
            rationale=(
                f"Field {field!r}: got {got!r}, expected {expected_val!r}."
            ),
            details={"field": field, "got": got, "expected": expected_val},
        )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _dig(obj: Any, path: str) -> Any:
    """Walk a dotted path through dicts/lists. Returns None if not found."""

    cur = obj
    for part in str(path).split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _eq(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is b
    return normalize_answer(str(a)) == normalize_answer(str(b))
