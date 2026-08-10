"""
Mock LLM Backend.

A deterministic, dependency-free LLM simulator that produces realistic
agent-style responses.  It analyses the prompt to choose an appropriate
response template, making the cross-framework network fully functional
without any API keys.

This is the default backend.  Set ``LLM_BACKEND=openai`` (with
``OPENAI_API_KEY``) to switch to a real model.
"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any

from llm.base import LLMBackend, LLMResponse


# ---------------------------------------------------------------------------
# Response templates keyed by detected intent
# ---------------------------------------------------------------------------
_RESEARCH_TEMPLATES = [
    # Used when the mock detects a research / information-gathering prompt.
    (
        "## Research Findings\n\n"
        "Based on analysis of the request, here are the key findings:\n\n"
        "1. **Overview**: {topic} is an active area with significant recent "
        "developments across multiple dimensions.\n\n"
        "2. **Key Facts**:\n"
        "   - Primary driver: adoption is growing at an estimated 25-40% annually\n"
        "   - Major stakeholders include research labs, enterprises, and open-source "
        "communities\n"
        "   - Regulatory frameworks are still maturing\n\n"
        "3. **Trends**:\n"
        "   - Increasing convergence between research and production deployments\n"
        "   - Growing emphasis on safety, observability, and interoperability\n"
        "   - Shift from monolithic systems toward modular, protocol-based "
        "architectures\n\n"
        "4. **Considerations**:\n"
        "   - Cost vs. latency trade-offs remain the primary design tension\n"
        "   - Standardization efforts (e.g. A2A, MCP) are reducing integration "
        "friction\n"
        "   - Talent gap in cross-framework expertise is a bottleneck\n\n"
        "5. **Outlook**: The next 12-18 months will likely see consolidation "
        "around a small set of interoperability standards, with production "
        "deployments moving from pilots to scaled systems.\n"
    ),
    (
        "## Research Report\n\n"
        "**Topic**: {topic}\n\n"
        "### Summary\n"
        "{topic} represents a significant development in the field. The "
        "following analysis synthesizes available information into a "
        "structured overview.\n\n"
        "### Background\n"
        "The subject has evolved through several phases, moving from "
        "theoretical foundations to practical implementation. Current "
        "momentum is driven by both technical advances and market demand.\n\n"
        "### Key Findings\n"
        "- **Technical maturity**: Moderate to high, with active development "
        "addressing remaining gaps.\n"
        "- **Adoption pattern**: Early adopters in technology and finance "
        "sectors, expanding to healthcare and education.\n"
        "- **Risk profile**: Manageable with proper governance, though "
        "long-term effects require monitoring.\n\n"
        "### Data Points\n"
        "| Metric | Value | Source |\n"
        "|--------|-------|--------|\n"
        "| Adoption rate | 32% | Industry survey |\n"
        "| Avg. ROI | 3.2x | Case studies |\n"
        "| Time to value | 4-8 weeks | Practitioner reports |\n\n"
        "### Conclusion\n"
        "The evidence supports cautious optimism. Organizations that invest "
        "in skills and infrastructure now are positioned to benefit as the "
        "ecosystem matures.\n"
    ),
]

_WRITING_TEMPLATES = [
    (
        "# {title}\n\n"
        "## Introduction\n\n"
        "{intro}\n\n"
        "## Main Content\n\n"
        "{body}\n\n"
        "## Conclusion\n\n"
        "{conclusion}\n\n"
        "---\n"
        "*This piece was crafted to balance clarity with depth, targeting "
        "an informed professional audience.*\n"
    ),
    (
        "{title}\n"
        "{'=' * len(title)}\n\n"
        "{intro}\n\n"
        "## Body\n\n"
        "{body}\n\n"
        "## Takeaways\n\n"
        "- {takeaway1}\n"
        "- {takeaway2}\n"
        "- {takeaway3}\n\n"
        "{conclusion}\n"
    ),
]

_GENERAL_TEMPLATES = [
    (
        "I've processed your request about: \"{query}\"\n\n"
        "Here is my response:\n\n"
        "Based on the information provided, the most relevant approach "
        "involves breaking the problem into manageable components, "
        "addressing each systematically, and synthesizing the results. "
        "This method ensures thoroughness while maintaining clarity. "
        "The key insight is that structured decomposition reduces "
        "cognitive load and improves outcome quality.\n"
    ),
    (
        "## Response\n\n"
        "**Query**: {query}\n\n"
        "**Analysis**: The request can be addressed through a combination "
        "of direct information retrieval and contextual reasoning. The "
        "following points capture the essential considerations.\n\n"
        "**Key Points**:\n"
        "1. The core question centers on practical applicability.\n"
        "2. Multiple valid approaches exist, each with distinct trade-offs.\n"
        "3. The recommended path balances efficiency with robustness.\n\n"
        "**Recommendation**: Proceed with a phased approach, validating "
        "assumptions at each step.\n"
    ),
]


def _detect_topic(prompt: str) -> str:
    """Extract a short topic string from the prompt."""
    # Remove common instruction prefixes.
    cleaned = re.sub(
        r"^(please\s+)?(research|write|analyze|summarize|explain|draft|create)\s+",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^(about|on|regarding)\s+", "", cleaned, flags=re.IGNORECASE)
    # Remove "User task:" / "Research Query:" style prefixes.
    cleaned = re.sub(
        r"^(user\s+task|research\s+query|writing\s+request|topic|query)\s*:\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Take the first sentence or first 80 chars.
    first_sentence = cleaned.split(".")[0].strip()
    if len(first_sentence) > 80:
        first_sentence = first_sentence[:77] + "..."
    return first_sentence or cleaned[:80]


def _is_planning_prompt(prompt: str, system: str | None) -> bool:
    """Detect if this is a task-decomposition / planning request."""
    combined = f"{system or ''} {prompt}".lower()
    markers = ["decompose", "planning assistant", "plan the structure", "break down"]
    return any(m in combined for m in markers)


def _is_synthesis_prompt(prompt: str, system: str | None) -> bool:
    """Detect if this is a synthesis / merge request."""
    combined = f"{system or ''} {prompt}".lower()
    markers = ["synthesis assistant", "synthesize", "sub-task results", "final synthesized"]
    return any(m in combined for m in markers)


def _generate_plan(prompt: str) -> str:
    """Generate a properly formatted 2-step plan for the given task."""
    # Extract the core task text.
    task_match = re.search(r"user task\s*:\s*(.+?)(?:\n|$)", prompt, re.IGNORECASE)
    task_text = task_match.group(1).strip() if task_match else prompt[:100]

    return (
        f"[research] Research the key aspects of: {task_text}\n"
        f"[writing] Write a polished piece based on the research findings"
    )


def _generate_synthesis(prompt: str) -> str:
    """Generate a synthesized response from sub-task results."""
    # Extract sub-task results from the prompt.
    parts = prompt.split("--- Sub-task:")
    sub_results = []
    for part in parts[1:]:  # skip the part before the first sub-task
        lines = part.strip().split("\n", 1)
        if len(lines) == 2:
            label = lines[0].strip().rstrip(" ---")
            content = lines[1].strip()[:300]
            sub_results.append((label, content))

    if not sub_results:
        return "Based on the completed sub-tasks, here is the synthesized result."

    # Build a coherent synthesis.
    sections = ["# Synthesized Result\n"]
    for label, content in sub_results:
        sections.append(f"## {label}\n\n{content}\n")

    sections.append(
        "\n## Conclusion\n\n"
        "The above sections represent the collaborative output of multiple "
        "specialized agents working through the A2A protocol. Each agent "
        "contributed its domain expertise, and the results have been merged "
        "into this final, coherent response."
    )
    return "\n".join(sections)


def _make_deterministic_choice(seed: str, options: list) -> Any:
    """Pick an element from options deterministically based on seed."""
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return options[h % len(options)]


class MockLLM(LLMBackend):
    """
    Deterministic mock LLM.

    Parameters:
        persona: Influences response style.  One of ``"research"``,
            ``"writing"``, ``"general"``.
        model_id: The model identifier reported in responses.
        base_latency_ms: Simulated latency (plus jitter) for realism.
    """

    def __init__(
        self,
        persona: str = "general",
        model_id: str = "mock-default",
        base_latency_ms: float = 50.0,
    ) -> None:
        self._persona = persona.lower().strip()
        self._model_id = model_id
        self._base_latency_ms = base_latency_ms

    @property
    def name(self) -> str:
        return f"MockLLM({self._persona})"

    @property
    def model_id(self) -> str:
        return self._model_id

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        # Simulate processing latency (deterministic jitter from prompt hash).
        h = int(hashlib.sha256(prompt.encode()).hexdigest(), 16)
        latency = self._base_latency_ms + (h % 80)
        time.sleep(latency / 1000.0)

        topic = _detect_topic(prompt)
        seed = f"{self._persona}:{prompt}"

        # Special handling for planning and synthesis prompts (used by
        # the supervisor) — these need structured output that the caller
        # parses, so they take priority over persona-based templates.
        if _is_planning_prompt(prompt, system):
            text = _generate_plan(prompt)
        elif _is_synthesis_prompt(prompt, system):
            text = _generate_synthesis(prompt)
        elif self._persona == "research":
            template = _make_deterministic_choice(seed, _RESEARCH_TEMPLATES)
            text = template.format(topic=topic)
        elif self._persona == "writing":
            template = _make_deterministic_choice(seed, _WRITING_TEMPLATES)
            title = topic.title() if len(topic) < 60 else topic[:57].title() + "..."
            intro = (
                f"In this piece, we explore {topic.lower()}. "
                f"This subject deserves careful attention because it touches "
                f"on several interconnected themes that shape the modern "
                f"landscape."
            )
            body = (
                f"The discussion around {topic.lower()} spans multiple "
                f"perspectives. On one hand, practitioners emphasize "
                f"practical implementation challenges. On the other, "
                f"theorists argue for foundational principles that should "
                f"guide all work in this area. The truth, as often happens, "
                f"lies in a synthesis of both views.\n\n"
                f"What makes {topic.lower()} particularly interesting is "
                f"its rapid evolution. Best practices that were dominant "
                f"just months ago are now being revised. This dynamism "
                f"is both a challenge and an opportunity—it rewards "
                f"those who stay informed and adapt quickly."
            )
            takeaway1 = "Structure matters more than volume in effective communication"
            takeaway2 = "Audience awareness shapes every stylistic choice"
            takeaway3 = "Revision is where good writing becomes great"
            conclusion = (
                f"As we look ahead, {topic.lower()} will continue to "
                f"evolve. The organizations and individuals who approach "
                f"it with curiosity, rigor, and adaptability will be "
                f"best positioned to thrive."
            )
            text = template.format(
                title=title,
                intro=intro,
                body=body,
                takeaway1=takeaway1,
                takeaway2=takeaway2,
                takeaway3=takeaway3,
                conclusion=conclusion,
            )
        else:
            template = _make_deterministic_choice(seed, _GENERAL_TEMPLATES)
            text = template.format(query=prompt[:200])

        # Token estimation (rough): ~4 chars per token.
        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4

        return LLMResponse(
            text=text,
            model=self._model_id,
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            latency_ms=latency,
            metadata={"persona": self._persona, "deterministic": True},
        )
