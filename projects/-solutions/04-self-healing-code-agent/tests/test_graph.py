"""End-to-end graph test using a scripted mock LLM.

The mock LLM is hand-tuned to emit the correct patch for case_01. This proves
the whole reproduce → diagnose → patch → verify → submit loop wires up
correctly without needing a real API key.
"""

from __future__ import annotations

import pytest

from self_heal.agent import RunConfig, SelfHealAgent
from self_heal.llm.base import LLMResponse, Message, TokenUsage
from self_heal.llm.mock import MockProvider


class ScriptedProvider(MockProvider):
    """Mock that returns a fixed diff for the patch step, regardless of input."""

    def complete(self, messages: list[Message]) -> LLMResponse:
        sys_msg = next((m for m in messages if m.role == "system"), None)
        sys_text = sys_msg.content if sys_msg else ""
        if "patch" in sys_text.lower() or "unified diff" in sys_text.lower():
            return LLMResponse(
                content=(
                    "```diff\n"
                    "--- a/src/calc.py\n"
                    "+++ b/src/calc.py\n"
                    "@@ -8,4 +8,4 @@\n"
                    "     total = 0\n"
                    "-    for i in range(start, end):  # bug: should be end + 1\n"
                    "+    for i in range(start, end + 1):\n"
                    "         total += i\n"
                    "     return total\n"
                    "```"
                ),
                usage=TokenUsage(input_tokens=100, output_tokens=50),
                model="scripted-mock",
            )
        return super().complete(messages)


@pytest.mark.integration
def test_graph_fixes_case_01_end_to_end(copy_fixture) -> None:
    case = copy_fixture("case_01_off_by_one")
    agent = SelfHealAgent(provider=ScriptedProvider())

    result = agent.run(
        RunConfig(
            repo_path=case,
            test_target="tests/test_calc.py::test_sum_range_basic",
            max_iterations=2,
            open_pr=False,
        )
    )

    assert result.status == "passed", f"expected passed, got {result.status}"
    assert result.iterations >= 1
    assert result.llm_calls >= 1

    # The fix should be persisted to disk.
    fixed = (case / "src" / "calc.py").read_text()
    assert "range(start, end + 1)" in fixed


@pytest.mark.integration
def test_graph_exhausts_iterations_on_unfixable_bug(copy_fixture) -> None:
    """If the mock never emits a working patch, the loop should exhaust."""
    case = copy_fixture("case_02_wrong_exception")

    # A mock that always returns a nonsense patch.
    class BadMock(MockProvider):
        def complete(self, messages: list[Message]) -> LLMResponse:
            sys_msg = next((m for m in messages if m.role == "system"), None)
            if sys_msg and "patch" in sys_msg.content.lower():
                return LLMResponse(
                    content="```diff\n--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,1 +1,1 @@\n-foo\n+bar\n```",
                    usage=TokenUsage(input_tokens=10, output_tokens=5),
                    model="bad-mock",
                )
            return super().complete(messages)

    agent = SelfHealAgent(provider=BadMock())
    result = agent.run(
        RunConfig(
            repo_path=case,
            test_target="tests/test_calc.py::test_divide_by_zero",
            max_iterations=2,
            open_pr=False,
        )
    )
    assert result.status in ("exhausted", "failed")


def test_agent_uses_mock_when_no_key() -> None:
    """With no API keys set, the factory should pick the mock provider."""
    from self_heal.config import LLMProviderName, Settings
    from self_heal.llm.base import provider_factory

    s = Settings(
        llm_provider=LLMProviderName.OPENAI,
        openai_api_key="",
        anthropic_api_key="",
    )
    provider = provider_factory(s)
    assert provider.name == "mock"
