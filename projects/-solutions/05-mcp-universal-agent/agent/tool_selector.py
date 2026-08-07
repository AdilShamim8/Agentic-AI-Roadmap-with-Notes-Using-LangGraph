"""Stage 3 of the agent loop: tool selection.

When the registry exposes 20+ tools, passing every tool to the LLM on every
turn degrades selection accuracy (the model gets distracted by irrelevant
tools). This module implements three mitigation strategies and a single
:class:`ToolSelector` facade that picks one based on env config.

Strategies
----------
``naive``
    Pass ALL tools every turn. The baseline. Cheapest to reason about, but
    the worst accuracy when the tool list is large.

``categorized``
    Two-stage call: (1) the LLM is given a short list of *categories*
    ("files", "math", "data", "web", "misc") and asked which category fits
    the user goal; (2) only tools from that category are then passed to the
    next agent turn. Halves the tool list seen by the LLM.

``retrieval``
    Embed every tool description with TF-IDF at startup, then for each user
    message retrieve the top-``k`` most similar tools and pass only those to
    the LLM. Best accuracy on the 20-tool registry; default strategy.

All three strategies produce an OpenAI-compatible ``tools`` array, so the
rest of the agent doesn't care which one is active.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from .discovery import ToolInfo
from .embeddings import TfIdfIndex
from .llm import LLM, LLMResponse, ToolCall


@dataclass
class SelectionResult:
    """The tools chosen for this turn, plus debug metadata."""

    tools: List[Dict]  # OpenAI-compatible tool definitions
    strategy: str
    rationale: str = ""  # human-readable hint for logs / evals


class ToolSelector:
    """Pick which tools the LLM sees on a given turn."""

    def __init__(
        self,
        all_tools: List[ToolInfo],
        strategy: Optional[str] = None,
        top_k: Optional[int] = None,
        llm: Optional[LLM] = None,
    ) -> None:
        self.all_tools = all_tools
        self.strategy = (strategy or os.environ.get("MCP_AGENT_SELECTION_STRATEGY", "retrieval")).lower()
        self.top_k = int(top_k or os.environ.get("MCP_AGENT_RETRIEVAL_TOP_K", "12"))
        self.llm = llm  # only used by the 'categorized' strategy
        self._index: Optional[TfIdfIndex] = None
        self._by_cat: Dict[str, List[ToolInfo]] = {}
        if self.strategy == "retrieval":
            # Index name (repeated to boost name-token weight) + category +
            # description so a query like "evaluate 5+5" matches the tool
            # NAME "calculator.evaluate" even when the description wording
            # doesn't overlap. Repeating the name tokens 3x makes a name
            # match dominate over a weak description match.
            self._index = TfIdfIndex().fit([
                f"{t.name} {t.name} {t.name} {t.category} {t.description}"
                for t in all_tools
            ])
        # Always compute the category map; cheap and useful for logging.
        for t in all_tools:
            self._by_cat.setdefault(t.category, []).append(t)

    # -- public --------------------------------------------------------------
    def select(self, user_message: str, history: List) -> SelectionResult:
        """Return the OpenAI-style tool list the LLM should see this turn."""
        history = _normalise_history(history)
        if self.strategy == "naive":
            return SelectionResult(
                tools=[self._to_openai_tool(t) for t in self.all_tools],
                strategy="naive",
                rationale=f"passed all {len(self.all_tools)} tools",
            )
        if self.strategy == "categorized":
            return self._select_categorized(user_message, history)
        if self.strategy == "retrieval":
            return self._select_retrieval(user_message, history)
        raise ValueError(f"Unknown selection strategy: {self.strategy!r}")

    # -- strategies ----------------------------------------------------------
    def _select_retrieval(self, user_message: str, history: List[Dict]) -> SelectionResult:
        assert self._index is not None
        # Use the latest user message + the latest assistant text as the
        # retrieval query. Including assistant text helps when the model
        # is mid-reasoning ("Let me now also calculate…").
        query = user_message
        for m in reversed(history):
            if m.get("role") == "assistant" and m.get("content"):
                query = f"{m['content']} {query}"
                break
        top = self._index.top_k(query, k=self.top_k)
        # Fallback: if the best score is very low (no real lexical overlap),
        # pass ALL tools. This prevents the agent from getting stuck when
        # the user's query has no keyword overlap with any tool description
        # (e.g. "What is 5 + 5" – the LLM still needs to SEE calculator.evaluate).
        if not top or top[0][1] < 0.05:
            return SelectionResult(
                tools=[self._to_openai_tool(t) for t in self.all_tools],
                strategy="retrieval",
                rationale=f"low-confidence retrieval (best={top[0][1] if top else 0:.3f}); fell back to all {len(self.all_tools)} tools",
            )
        chosen_indices = {i for i, _ in top}
        chosen = [self.all_tools[i] for i, _ in top]
        # Category-completeness guarantee: if ANY tool from a category is
        # retrieved, ensure the "primary" tool of that category is also
        # offered. This matters for short queries like "5 + 5" where
        # retrieval may surface calculator.statistics (because "5" matches
        # "list of numbers") but miss calculator.evaluate (the tool the LLM
        # actually needs). The primary tool is the first one defined per
        # category in registry order.
        seen_cats = {t.category for t in chosen}
        for cat in seen_cats:
            primary = self._by_cat[cat][0]  # first tool = primary, by registry order
            if primary.name not in {t.name for t in chosen}:
                chosen.append(primary)
        return SelectionResult(
            tools=[self._to_openai_tool(t) for t in chosen],
            strategy="retrieval",
            rationale=f"retrieved top {len(chosen)} of {len(self.all_tools)} tools (best={top[0][1]:.3f})",
        )

    def _select_categorized(self, user_message: str, history: List[Dict]) -> SelectionResult:
        """Two-stage selection: pick a category with the LLM, then expose
        only that category's tools.

        If no LLM is available (e.g. mock mode without API key), fall back
        to keyword matching on the category names.
        """
        # Build a "category picker" tool and ask the LLM to call it.
        categories = sorted(self._by_cat.keys())
        # Use the keyword fallback when no LLM is wired in OR the LLM is the
        # deterministic mock (which has no rule for the synthetic
        # "pick_category" tool and would always pick the default category).
        if self.llm is None or getattr(self.llm, "name", "") == "mock":
            # Keyword fallback when no LLM is wired in.
            text = user_message.lower()
            cat = "misc"
            if any(w in text for w in ("file", "read", "write", "search file")):
                cat = "files"
            elif any(w in text for w in ("calc", "math", "convert", "sqrt", "log", "average", "percent")) \
                    or any(op in text for op in ("+", "*", "/", "%")):
                cat = "math"
            elif any(w in text for w in ("sql", "table", "query", "database")):
                cat = "data"
            elif any(w in text for w in ("web", "weather", "news", "search the", "fetch")):
                cat = "web"
            chosen = self._by_cat.get(cat, self.all_tools)
            return SelectionResult(
                tools=[self._to_openai_tool(t) for t in chosen],
                strategy="categorized",
                rationale=f"keyword-picked category '{cat}' ({len(chosen)} tools)",
            )

        # LLM path: ask the model to pick a category.
        picker_tool = {
            "type": "function",
            "function": {
                "name": "pick_category",
                "description": "Pick the single tool category that best matches the user goal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": categories},
                    },
                    "required": ["category"],
                },
            },
        }
        resp: LLMResponse = self.llm(
            [{"role": "user", "content": user_message}],
            [picker_tool],
        )
        cat = "misc"
        if resp.tool_calls:
            cat = resp.tool_calls[0].arguments.get("category", "misc")
        chosen = self._by_cat.get(cat, self.all_tools)
        return SelectionResult(
            tools=[self._to_openai_tool(t) for t in chosen],
            strategy="categorized",
            rationale=f"LLM picked category '{cat}' ({len(chosen)} tools)",
        )

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _to_openai_tool(t: ToolInfo) -> Dict:
        """Convert a :class:`ToolInfo` to the OpenAI ``tools`` array format."""
        return {
            "type": "function",
            "function": {
                "name": t.name,
                "description": f"[{t.category}] {t.description}",
                "parameters": t.input_schema,
            },
        }


def _normalise_history(history: List) -> List[Dict]:
    """Convert a list of LangChain ``BaseMessage`` objects (or plain dicts)
    into a uniform list of dicts with ``role`` and ``content`` keys.

    LangGraph's ``add_messages`` reducer converts dict messages to
    ``HumanMessage`` / ``AIMessage`` / etc., so any node that looks at
    ``state['messages']`` may receive either form. This helper papers over
    the difference for the selector.
    """
    out: List[Dict] = []
    for m in history or []:
        if isinstance(m, dict):
            out.append(m)
            continue
        # LangChain BaseMessage: .type is "human"/"ai"/"system"/"tool".
        # Map back to the OpenAI role names the LLM providers expect.
        t = getattr(m, "type", "") or ""
        role = {"human": "user", "ai": "assistant"}.get(t, t)
        entry = {"role": role, "content": getattr(m, "content", "") or ""}
        # Preserve tool_call_id / tool_calls if present.
        additional = getattr(m, "additional_kwargs", {}) or {}
        if "tool_call_id" in additional:
            entry["tool_call_id"] = additional["tool_call_id"]
        if additional.get("tool_calls"):
            entry["tool_calls"] = additional["tool_calls"]
        out.append(entry)
    return out
