"""LLM-as-judge evaluator.

Calls an LLM with a rubric prompt and parses a 0-1 score + rationale.

Three providers are supported:

- `mock` (default): deterministic stub that scores based on string overlap
  with the expected answer. No API key needed. Reproducible to the byte.
- `openai`: calls the OpenAI chat completions API. Requires OPENAI_API_KEY.
- `anthropic`: calls the Anthropic messages API. Requires ANTHROPIC_API_KEY.

The mock provider exists so the harness is fully usable offline and so
inter-rater reliability tests against `rule_based` are meaningful.
"""

from __future__ import annotations

import json
import re
import textwrap
from typing import Any, Protocol

from eval.evaluators.base import BaseEvaluator
from eval.schemas import AgentOutput, DatasetRow, EvalResult, Trajectory
from eval.utils import answer_to_str, normalize_answer
from eval.config import get_settings


# ---------------------------------------------------------------------------
# LLM client protocol
# ---------------------------------------------------------------------------


class LLMClient(Protocol):
    """Anything that can take a (system, user) prompt and return a string."""

    def complete(self, system: str, user: str) -> str: ...


# ---------------------------------------------------------------------------
# Mock provider (deterministic, offline)
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Deterministic stub.

    Scores = Jaccard overlap of normalised token sets between the agent
    answer and the expected answer, with a small penalty for forbidden
    substrings.

    This is deliberately *not* a great judge — its purpose is to be a
    reproducible baseline that you can run `eval kappa` against.
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def complete(self, system: str, user: str) -> str:
        # The user message ends with a JSON block containing the answer +
        # expected. We parse it out, compute a deterministic score, and
        # return a JSON block that the parser will accept.
        try:
            payload = _extract_json(user)
        except Exception:
            payload = {}
        answer = payload.get("answer", "")
        expected = payload.get("expected", "")
        must_contain = payload.get("must_contain", []) or []

        got_tokens = set(normalize_answer(answer).split())
        exp_tokens = set(normalize_answer(expected).split())
        if not got_tokens and not exp_tokens:
            overlap = 1.0
        elif not exp_tokens:
            overlap = 1.0
        else:
            union = got_tokens | exp_tokens
            overlap = len(got_tokens & exp_tokens) / max(1, len(union))

        # Bonus: did we hit all must_contain?
        if must_contain:
            text_lower = answer.lower()
            hits = sum(1 for s in must_contain if s.lower() in text_lower)
            overlap = 0.5 * overlap + 0.5 * (hits / len(must_contain))

        score = round(max(0.0, min(1.0, overlap)), 3)
        passed = score >= 0.7
        rationale = (
            "Mock judge: token-overlap score."
            if passed
            else "Mock judge: insufficient token overlap with expected answer."
        )
        return json.dumps({"score": score, "passed": passed, "rationale": rationale})


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class OpenAILLMClient:
    """Thin wrapper over the OpenAI chat completions API."""

    def __init__(self, api_key: str, model: str, temperature: float = 0.0) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "openai is not installed. Run `pip install openai` or use "
                "EVAL_LLM_PROVIDER=mock."
            ) from exc
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def complete(self, system: str, user: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------


class AnthropicLLMClient:
    """Thin wrapper over the Anthropic messages API."""

    def __init__(self, api_key: str, model: str, temperature: float = 0.0) -> None:
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "anthropic is not installed. Run `pip install anthropic` or "
                "use EVAL_LLM_PROVIDER=mock."
            ) from exc
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def complete(self, system: str, user: str) -> str:
        resp = self.client.messages.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # The Anthropic SDK returns content blocks.
        parts = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_llm_client(provider: str | None = None) -> LLMClient:
    """Build an LLM client based on settings."""

    s = get_settings()
    provider = provider or s.llm_provider
    if provider == "mock":
        return MockLLMClient(seed=s.seed)
    if provider == "openai":
        if not s.openai_api_key:
            raise RuntimeError("EVAL_LLM_PROVIDER=openai but OPENAI_API_KEY is unset.")
        return OpenAILLMClient(s.openai_api_key, s.openai_model, s.llm_temperature)
    if provider == "anthropic":
        if not s.anthropic_api_key:
            raise RuntimeError(
                "EVAL_LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is unset."
            )
        return AnthropicLLMClient(s.anthropic_api_key, s.anthropic_model, s.llm_temperature)
    raise ValueError(f"Unknown LLM provider: {provider!r}")


# ---------------------------------------------------------------------------
# The evaluator
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an evaluation judge. You will be given an agent's answer and a
    reference expected answer. Score the agent's answer on a 0-1 scale
    according to the rubric below, and explain your reasoning in one
    sentence.

    Rubric:
      1.0  Perfect — answer is semantically equivalent to the expected.
      0.7  Mostly correct — minor omissions / phrasing differences.
      0.4  Partial — correct direction but material errors.
      0.0  Wrong — answer does not address the question.

    You MUST respond with a single JSON object, no prose before or after:
      {"score": <float>, "passed": <bool>, "rationale": "<one sentence>"}
    """
).strip()


_USER_TEMPLATE = textwrap.dedent(
    """
    Question:
    {question}

    Agent answer:
    {answer}

    Expected answer:
    {expected}

    Must contain: {must_contain}
    Must NOT contain: {must_not_contain}

    Input payload (for programmatic judges):
    {payload}

    Respond with JSON only:
    {{
      "score": <0.0-1.0>,
      "passed": <true if score >= 0.7>,
      "rationale": "<one short sentence>"
    }}
    """
).strip()


class LLMJudgeEvaluator(BaseEvaluator):
    """LLM-as-judge evaluator.

    Params:
        provider: 'mock' | 'openai' | 'anthropic'. Defaults to settings.
        rubric: optional override for the system prompt.
        pass_threshold: score above which `passed=True`. Default 0.7.
    """

    name = "llm_judge"

    def __init__(self, **params: Any) -> None:
        super().__init__(**params)
        self._client: LLMClient | None = None
        self.pass_threshold = float(params.get("pass_threshold", 0.7))
        self.rubric = params.get("rubric", _SYSTEM_PROMPT)

    @property
    def client(self) -> LLMClient:
        if self._client is None:
            self._client = build_llm_client(self.params.get("provider"))
        return self._client

    def evaluate(
        self,
        row: DatasetRow,
        output: AgentOutput,
        trajectory: Trajectory | None = None,
    ) -> EvalResult:
        answer = answer_to_str(output.answer)
        expected = answer_to_str(row.expected.answer)
        payload = json.dumps(
            {
                "question": row.input,
                "answer": answer,
                "expected": expected,
                "must_contain": row.expected.must_contain or [],
                "must_not_contain": row.expected.must_not_contain or [],
            },
            ensure_ascii=False,
        )
        user = _USER_TEMPLATE.format(
            question=row.input,
            answer=answer,
            expected=expected,
            must_contain=row.expected.must_contain or [],
            must_not_contain=row.expected.must_not_contain or [],
            payload=payload,
        )
        raw = self.client.complete(self.rubric, user)
        score, passed, rationale = _parse_judge_output(raw, self.pass_threshold)
        return EvalResult(
            evaluator=self.display_name(),
            row_id=row.id,
            passed=passed,
            score=score,
            rationale=rationale,
            details={"raw": raw[:500]},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_JSON_RE = re.compile(r"\{[\s\S]*?\}(?=\s*\n|\s*$)")


def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first valid JSON {...} block from text.

    Tries each `{...}` match in order and returns the first that parses.
    Robust to extra prose around the JSON and to multiple JSON blocks
    in the same text (e.g. an input payload + a response template).
    """

    for m in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    # Fall back to greedy match.
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def _parse_judge_output(raw: str, threshold: float) -> tuple[float, bool, str]:
    """Parse the judge's JSON output into (score, passed, rationale).

    Robust to: extra prose around the JSON, missing fields, malformed numbers.
    """

    payload = _extract_json(raw)
    score = float(payload.get("score", 0.0))
    score = max(0.0, min(1.0, score))
    passed = bool(payload.get("passed", score >= threshold))
    rationale = str(payload.get("rationale", "No rationale provided."))[:300]
    return score, passed, rationale
