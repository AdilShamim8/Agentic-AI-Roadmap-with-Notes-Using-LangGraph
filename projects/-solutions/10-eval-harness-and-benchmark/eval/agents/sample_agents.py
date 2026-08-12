"""Sample agents — one per pattern.

These are *deliberately simple* rule-based stubs that produce the right
shape of output for their pattern. They are NOT meant to be impressive
agents — they exist so the harness has something to evaluate end-to-end
without requiring an LLM.

Replace them with your real LangGraph / OpenAI Agents SDK / CrewAI agent
via `examples/custom_agent.py`.
"""

from __future__ import annotations

import re
from typing import Any

from eval.agents.base import BaseAgent
from eval.schemas import AgentOutput, ToolCall, Trajectory, TrajectoryStep


# ---------------------------------------------------------------------------
# Helpers shared by all sample agents
# ---------------------------------------------------------------------------


_KB: dict[str, str] = {
    "capital of france": "Paris",
    "capital of japan": "Tokyo",
    "capital of bangladesh": "Dhaka",
    "capital of germany": "Berlin",
    "capital of brazil": "Brasilia",
    "capital of canada": "Ottawa",
    "capital of egypt": "Cairo",
    "capital of australia": "Canberra",
    "capital of india": "New Delhi",
    "capital of kenya": "Nairobi",
    "population of france": "about 68 million",
    "population of japan": "about 125 million",
    "population of bangladesh": "about 170 million",
    "author of romeo and juliet": "William Shakespeare",
    "author of the odyssey": "Homer",
    "chemical symbol for gold": "Au",
    "chemical symbol for water": "H2O",
    "chemical symbol for salt": "NaCl",
    "square root of 144": "12",
    "square root of 256": "16",
    "largest planet in the solar system": "Jupiter",
    "smallest planet in the solar system": "Mercury",
    "speed of light in vacuum": "299792458 m/s",
    "boiling point of water at sea level": "100 degrees Celsius",
    "currency of japan": "Japanese Yen",
    "currency of bangladesh": "Bangladeshi Taka",
    "currency of the european union": "Euro",
    "primary language of brazil": "Portuguese",
    "primary language of egypt": "Arabic",
}


def _lookup(question: str) -> str | None:
    q = question.strip().lower().rstrip("?.,!")
    # Try a direct lookup.
    if q in _KB:
        return _KB[q]
    # Try a substring match.
    for key, val in _KB.items():
        if key in q:
            return val
    return None


def _extract_number(text: str) -> int | None:
    m = re.search(r"\b(\d+)\b", text)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# 1. ReAct (Reason + Act)
# ---------------------------------------------------------------------------


class ReActSampleAgent(BaseAgent):
    """A toy ReAct agent: Thought → Action → Observation → ... → Answer.

    Uses an internal KB lookup as its only "tool".
    """

    name = "ReActSampleAgent"
    pattern = "react"

    def run(self, input: str) -> AgentOutput:
        steps: list[TrajectoryStep] = []

        steps.append(
            TrajectoryStep(
                thought=f"I need to answer: {input!r}. I'll search my knowledge base.",
                action="search_kb",
            )
        )
        result = _lookup(input) or "I don't know."
        steps.append(
            TrajectoryStep(
                thought="I got an observation from the KB.",
                action="search_kb",
                tool_call=ToolCall(name="search_kb", args={"query": input}, result=result),
                observation=result,
            )
        )
        steps.append(
            TrajectoryStep(
                thought="I have enough information to answer.",
                action="finish",
            )
        )
        return AgentOutput(
            answer=result,
            trajectory=Trajectory(steps=steps, metadata={"pattern": "react"}),
            metadata={"n_steps": len(steps)},
        )


# ---------------------------------------------------------------------------
# 2. Plan-and-Execute
# ---------------------------------------------------------------------------


class PlanExecuteSampleAgent(BaseAgent):
    """A toy plan-and-execute agent.

    Plans a list of sub-questions, executes each one with the KB lookup,
    and synthesises a final answer.
    """

    name = "PlanExecuteSampleAgent"
    pattern = "plan_execute"

    def run(self, input: str) -> AgentOutput:
        steps: list[TrajectoryStep] = []

        # Plan: split the input on "and" / "," / "then" into sub-questions.
        sub_qs = [s.strip() for s in re.split(r"\s+and\s+|,|\s+then\s+", input) if s.strip()]
        if len(sub_qs) <= 1:
            sub_qs = [input]

        steps.append(
            TrajectoryStep(
                thought=f"I'll split this into {len(sub_qs)} sub-question(s): {sub_qs}.",
                action="plan",
            )
        )

        results: list[str] = []
        for i, q in enumerate(sub_qs):
            r = _lookup(q) or f"unknown ({q})"
            results.append(r)
            steps.append(
                TrajectoryStep(
                    thought=f"Sub-question {i + 1}: {q!r}",
                    action="execute_step",
                    tool_call=ToolCall(name="search_kb", args={"query": q}, result=r),
                    observation=r,
                )
            )

        final = "; ".join(results) if len(results) > 1 else results[0]
        steps.append(
            TrajectoryStep(
                thought="All sub-questions answered. Synthesising final answer.",
                action="synthesize",
            )
        )
        return AgentOutput(
            answer=final,
            trajectory=Trajectory(steps=steps, metadata={"pattern": "plan_execute"}),
            metadata={"n_subquestions": len(sub_qs)},
        )


# ---------------------------------------------------------------------------
# 3. Supervisor (routes to specialist sub-agents)
# ---------------------------------------------------------------------------


class SupervisorSampleAgent(BaseAgent):
    """A toy supervisor agent.

    Inspects the input, routes to one of two specialist sub-agents
    (math / geography), and returns the sub-agent's answer.
    """

    name = "SupervisorSampleAgent"
    pattern = "supervisor"

    def run(self, input: str) -> AgentOutput:
        steps: list[TrajectoryStep] = []
        q = input.lower()

        if any(w in q for w in ["square root", "square", "sum", "product", "multiply", "divide"]):
            specialist = "math_specialist"
            answer = self._math(input)
        elif any(w in q for w in ["capital", "population", "currency", "language"]):
            specialist = "geography_specialist"
            answer = _lookup(input) or "unknown"
        else:
            specialist = "general_specialist"
            answer = _lookup(input) or "I don't know."

        steps.append(
            TrajectoryStep(
                thought=f"Classified input; routing to {specialist}.",
                action="route",
                tool_call=ToolCall(name="route", args={"to": specialist}, result=answer),
            )
        )
        steps.append(
            TrajectoryStep(
                thought=f"Specialist {specialist} returned: {answer!r}.",
                action="delegate",
                tool_call=ToolCall(name=specialist, args={"input": input}, result=answer),
                observation=answer,
            )
        )
        return AgentOutput(
            answer=answer,
            trajectory=Trajectory(steps=steps, metadata={"pattern": "supervisor"}),
            metadata={"specialist": specialist},
        )

    def _math(self, input: str) -> str:
        # Very small arithmetic support.
        m = re.search(r"square root of (\d+)", input, flags=re.IGNORECASE)
        if m:
            n = int(m.group(1))
            root = int(n ** 0.5)
            if root * root == n:
                return str(root)
            return f"about {n ** 0.5:.4f}"
        m = re.search(r"(\d+)\s*[\+\-]\s*(\d+)", input)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            op = "+" if "+" in input else "-"
            return str(a + b if op == "+" else a - b)
        m = re.search(r"(\d+)\s*[\*x]\s*(\d+)", input, flags=re.IGNORECASE)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return str(a * b)
        return "I can't solve that."


# ---------------------------------------------------------------------------
# 4. Swarm (multiple specialists collaborate)
# ---------------------------------------------------------------------------


class SwarmSampleAgent(BaseAgent):
    """A toy swarm agent.

    Sends the question to *all* specialists in parallel, then has a
    "synthesiser" agent pick the best answer.
    """

    name = "SwarmSampleAgent"
    pattern = "swarm"

    def run(self, input: str) -> AgentOutput:
        steps: list[TrajectoryStep] = []

        # Each "specialist" looks at the question.
        candidates: dict[str, str] = {
            "math_specialist": self._math(input),
            "geography_specialist": _lookup(input) or "",
            "general_specialist": _lookup(input) or "I don't know.",
        }
        for name, ans in candidates.items():
            steps.append(
                TrajectoryStep(
                    thought=f"Specialist {name} answering.",
                    action="specialist_answer",
                    tool_call=ToolCall(name=name, args={"input": input}, result=ans),
                    observation=ans,
                )
            )

        # Synthesiser picks the first non-empty, non-"unknown" answer.
        chosen = next(
            (v for v in candidates.values() if v and "unknown" not in v.lower()),
            "I don't know.",
        )
        steps.append(
            TrajectoryStep(
                thought="Synthesiser picking the best answer.",
                action="synthesize",
                tool_call=ToolCall(
                    name="synthesize", args={"candidates": list(candidates.values())},
                    result=chosen,
                ),
                observation=chosen,
            )
        )
        return AgentOutput(
            answer=chosen,
            trajectory=Trajectory(steps=steps, metadata={"pattern": "swarm"}),
            metadata={"candidates": candidates},
        )

    def _math(self, input: str) -> str:
        m = re.search(r"square root of (\d+)", input, flags=re.IGNORECASE)
        if m:
            n = int(m.group(1))
            root = int(n ** 0.5)
            if root * root == n:
                return str(root)
        return ""


# ---------------------------------------------------------------------------
# 5. Map-Reduce
# ---------------------------------------------------------------------------


class MapReduceSampleAgent(BaseAgent):
    """A toy map-reduce agent.

    Splits the input into chunks (map), processes each chunk (map step),
    then combines the results (reduce step).
    """

    name = "MapReduceSampleAgent"
    pattern = "map_reduce"

    def run(self, input: str) -> AgentOutput:
        steps: list[TrajectoryStep] = []

        # Map: split into atomic facts / sub-questions.
        if " and " in input or "," in input:
            chunks = [c.strip() for c in re.split(r"\s+and\s+|,", input) if c.strip()]
        else:
            # Treat each word as a chunk (good for "list the capitals of X Y Z").
            m = re.findall(r"([A-Z][a-zA-Z]+)", input)
            chunks = m if len(m) >= 2 else [input]

        steps.append(
            TrajectoryStep(
                thought=f"Split input into {len(chunks)} chunk(s): {chunks}.",
                action="map_split",
            )
        )

        partial: list[str] = []
        for i, chunk in enumerate(chunks):
            r = _lookup(chunk) or _lookup(input) or f"unknown ({chunk})"
            partial.append(r)
            steps.append(
                TrajectoryStep(
                    thought=f"Mapping chunk {i + 1}: {chunk!r}",
                    action="map",
                    tool_call=ToolCall(name="lookup", args={"chunk": chunk}, result=r),
                    observation=r,
                )
            )

        # Reduce: join with "; ".
        final = "; ".join(partial) if len(partial) > 1 else (partial[0] if partial else "")
        steps.append(
            TrajectoryStep(
                thought="Reducing partial results into final answer.",
                action="reduce",
                tool_call=ToolCall(name="reduce", args={"partials": partial}, result=final),
                observation=final,
            )
        )
        return AgentOutput(
            answer=final,
            trajectory=Trajectory(steps=steps, metadata={"pattern": "map_reduce"}),
            metadata={"n_chunks": len(chunks)},
        )
