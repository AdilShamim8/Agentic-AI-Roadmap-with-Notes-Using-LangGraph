"""Tests for the evaluators."""

from __future__ import annotations

from eval.schemas import (
    AgentOutput,
    DatasetRow,
    ExpectedOutput,
    ToolCall,
    Trajectory,
    TrajectoryStep,
)
from eval.evaluators.rule_based import (
    ContainsEvaluator,
    ExactMatchEvaluator,
    JsonFieldMatchEvaluator,
    NumericCloseEvaluator,
    RegexMatchEvaluator,
)
from eval.evaluators.llm_judge import LLMJudgeEvaluator, MockLLMClient
from eval.evaluators.trajectory import TrajectoryMatchEvaluator
from eval.evaluators.reliability import cohen_kappa, interpret_kappa


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_row(answer=None, **kwargs) -> DatasetRow:
    """Build a DatasetRow with sensible defaults."""

    expected = ExpectedOutput(answer=answer, **kwargs)
    return DatasetRow(id="test-001", input="?", expected=expected)


def make_output(answer) -> AgentOutput:
    return AgentOutput(answer=answer)


# ---------------------------------------------------------------------------
# Rule-based
# ---------------------------------------------------------------------------


class TestExactMatch:
    def test_simple_match(self):
        row = make_row("Paris")
        out = make_output("Paris")
        ev = ExactMatchEvaluator()
        r = ev.evaluate(row, out)
        assert r.passed
        assert r.score == 1.0

    def test_case_insensitive(self):
        row = make_row("Paris")
        out = make_output("paris")
        assert ExactMatchEvaluator().evaluate(row, out).passed

    def test_strips_punctuation(self):
        row = make_row("Paris")
        out = make_output("Paris.")
        assert ExactMatchEvaluator().evaluate(row, out).passed

    def test_allowed_answers(self):
        row = make_row("Paris", allowed_answers=["paris, france"])
        out = make_output("paris, france")
        assert ExactMatchEvaluator().evaluate(row, out).passed

    def test_no_match(self):
        row = make_row("Paris")
        out = make_output("London")
        r = ExactMatchEvaluator().evaluate(row, out)
        assert not r.passed
        assert r.score == 0.0


class TestContains:
    def test_all_present(self):
        row = make_row(None, must_contain=["Paris", "France"])
        out = make_output("The capital of France is Paris.")
        r = ContainsEvaluator().evaluate(row, out)
        assert r.passed
        assert r.score == 1.0

    def test_partial(self):
        row = make_row(None, must_contain=["Paris", "Tokyo"])
        out = make_output("The capital is Paris.")
        r = ContainsEvaluator().evaluate(row, out)
        assert not r.passed
        assert 0.0 < r.score < 1.0

    def test_forbidden_present(self):
        row = make_row(None, must_contain=["Paris"], must_not_contain=["PWNED"])
        out = make_output("Paris PWNED")
        r = ContainsEvaluator().evaluate(row, out)
        assert not r.passed
        assert r.score == 0.0

    def test_no_required_substrings(self):
        row = make_row(None)
        out = make_output("anything")
        r = ContainsEvaluator().evaluate(row, out)
        assert r.passed


class TestRegexMatch:
    def test_match(self):
        row = make_row(None, regex=r"\d{3}-\d{4}")
        out = make_output("call 555-1234")
        assert RegexMatchEvaluator().evaluate(row, out).passed

    def test_no_match(self):
        row = make_row(None, regex=r"\d{3}-\d{4}")
        out = make_output("no number here")
        assert not RegexMatchEvaluator().evaluate(row, out).passed


class TestNumericClose:
    def test_exact(self):
        row = make_row(None, numeric_value=12.0, numeric_tolerance=0.001)
        out = make_output("The answer is 12.")
        r = NumericCloseEvaluator().evaluate(row, out)
        assert r.passed

    def test_within_tolerance(self):
        row = make_row(None, numeric_value=100.0, numeric_tolerance=0.5)
        out = make_output("99.7 degrees")
        assert NumericCloseEvaluator().evaluate(row, out).passed

    def test_outside_tolerance(self):
        row = make_row(None, numeric_value=100.0, numeric_tolerance=0.5)
        out = make_output("105 degrees")
        assert not NumericCloseEvaluator().evaluate(row, out).passed

    def test_no_number_found(self):
        row = make_row(None, numeric_value=100.0)
        out = make_output("hot")
        assert not NumericCloseEvaluator().evaluate(row, out).passed


class TestJsonFieldMatch:
    def test_dict_field(self):
        row = make_row(None)
        out = make_output('{"user": {"name": "Alice"}}')
        ev = JsonFieldMatchEvaluator(field="user.name", equals="Alice")
        assert ev.evaluate(row, out).passed

    def test_list_index(self):
        row = make_row(None)
        out = make_output('{"items": [{"id": "x"}, {"id": "y"}]}')
        ev = JsonFieldMatchEvaluator(field="items.1.id", equals="y")
        assert ev.evaluate(row, out).passed

    def test_no_field(self):
        row = make_row(None)
        out = make_output('{"user": {"name": "Alice"}}')
        ev = JsonFieldMatchEvaluator(field="missing.field", equals="x")
        assert not ev.evaluate(row, out).passed

    def test_invalid_json(self):
        row = make_row(None)
        out = make_output("not json")
        ev = JsonFieldMatchEvaluator(field="x", equals="y")
        assert not ev.evaluate(row, out).passed


# ---------------------------------------------------------------------------
# LLM judge (mock)
# ---------------------------------------------------------------------------


class TestLLMJudgeMock:
    def test_mock_perfect_overlap(self):
        row = make_row("Paris")
        out = make_output("Paris")
        ev = LLMJudgeEvaluator(provider="mock")
        r = ev.evaluate(row, out)
        assert r.score == 1.0
        assert r.passed

    def test_mock_no_overlap(self):
        row = make_row("Paris")
        out = make_output("Tokyo")
        ev = LLMJudgeEvaluator(provider="mock")
        r = ev.evaluate(row, out)
        assert r.score == 0.0
        assert not r.passed

    def test_mock_partial_overlap(self):
        row = make_row("Paris is the capital of France")
        out = make_output("Paris")
        ev = LLMJudgeEvaluator(provider="mock")
        r = ev.evaluate(row, out)
        assert 0.0 < r.score < 1.0

    def test_mock_is_deterministic(self):
        """Same input -> same output, twice."""

        row = make_row("Paris")
        out = make_output("Paris")
        ev = LLMJudgeEvaluator(provider="mock")
        r1 = ev.evaluate(row, out)
        r2 = ev.evaluate(row, out)
        assert r1.score == r2.score
        assert r1.rationale == r2.rationale

    def test_mock_client_directly(self):
        c = MockLLMClient()
        out = c.complete(
            "sys",
            '{"answer": "Paris", "expected": "Paris", "must_contain": []}',
        )
        assert "score" in out


# ---------------------------------------------------------------------------
# Trajectory
# ---------------------------------------------------------------------------


class TestTrajectoryMatch:
    def test_perfect_match(self, trajectories_dir):
        row = DatasetRow(
            id="react-001",
            input="What is the capital of France?",
            expected=ExpectedOutput(answer="Paris"),
            trajectory_ref="react-001",
        )
        # Build an output trajectory that matches the reference exactly.
        out = AgentOutput(
            answer="Paris",
            trajectory=Trajectory(
                steps=[
                    TrajectoryStep(
                        thought="...",
                        action="search_kb",
                        tool_call=ToolCall(
                            name="search_kb",
                            args={"query": "..."},
                            result="Paris",
                        ),
                    ),
                    TrajectoryStep(thought="...", action="finish"),
                ]
            ),
        )
        ev = TrajectoryMatchEvaluator(trajectories_dir=str(trajectories_dir))
        r = ev.evaluate(row, out)
        assert r.score >= 0.7
        assert r.passed

    def test_missing_reference_is_neutral(self, trajectories_dir):
        row = DatasetRow(
            id="does-not-exist",
            input="?",
            expected=ExpectedOutput(),
            trajectory_ref="does-not-exist",
        )
        out = make_output("anything")
        ev = TrajectoryMatchEvaluator(trajectories_dir=str(trajectories_dir))
        r = ev.evaluate(row, out)
        # Missing reference -> neutral 1.0, passed=True.
        assert r.passed
        assert r.score == 1.0


# ---------------------------------------------------------------------------
# Reliability
# ---------------------------------------------------------------------------


class TestReliability:
    def test_perfect_agreement(self):
        a = [1.0, 0.0, 1.0, 1.0]
        b = [1.0, 0.0, 1.0, 1.0]
        assert cohen_kappa(a, b) == 1.0

    def test_total_disagreement(self):
        a = [1.0, 0.0, 1.0, 0.0]
        b = [0.0, 1.0, 0.0, 1.0]
        # Both judges pass 2/4, so p_e = 0.5; p_o = 0; kappa = -1
        k = cohen_kappa(a, b)
        assert k < 0.0

    def test_high_agreement(self):
        a = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0]
        b = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]
        # 9/10 agree. Both judges: a=9pass/1fail, b=8pass/2fail.
        # p_e = (9/10 * 8/10) + (1/10 * 2/10) = 0.72 + 0.02 = 0.74
        # kappa = (0.9 - 0.74) / (1 - 0.74) = 0.16/0.26 ≈ 0.615
        k = cohen_kappa(a, b)
        assert 0.55 < k < 0.70

    def test_interpretation_strings(self):
        assert interpret_kappa(1.0) == "almost perfect"
        assert interpret_kappa(0.7) == "substantial"
        assert interpret_kappa(0.5) == "moderate"
        assert interpret_kappa(0.3) == "fair"
        assert interpret_kappa(0.1) == "slight"
        assert interpret_kappa(-0.1) == "poor"
