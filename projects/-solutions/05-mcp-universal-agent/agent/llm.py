"""LLM abstraction for the universal MCP agent.

The agent talks to the LLM through a single :class:`LLM` interface so it can
swap providers (OpenAI, Anthropic, deterministic mock) without touching the
orchestration code.

Provider auto-detection:

1. If ``MCP_AGENT_USE_MOCK_LLM=true``  -> :class:`MockLLM`
2. Else if ``OPENAI_API_KEY`` is set   -> :class:`OpenAILLM`
3. Else if ``ANTHROPIC_API_KEY`` is set-> :class:`AnthropicLLM`
4. Else fall back to :class:`MockLLM`  (so the project always runs)

The :class:`MockLLM` is intentionally simple: it pattern-matches on the user
goal to pick tools. It exists so that the agent loop can be smoke-tested in
CI without an API key. For real workloads use OpenAI or Anthropic.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """A single tool invocation requested by the LLM."""

    id: str
    name: str  # fully-qualified tool name, e.g. "filesystem.read_file"
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """The LLM's reply for one turn.

    Either ``text`` (final answer) or ``tool_calls`` (continue the loop) is
    populated. Both can be populated – the agent will execute the tool calls
    first and feed results back in the next turn.
    """

    text: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw: Any = None  # provider-specific object, for debugging


class LLM:
    """Abstract LLM interface. Concrete providers implement ``__call__``."""

    name: str = "base"

    def __call__(self, messages: List[Dict], tools: List[Dict]) -> LLMResponse:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
class OpenAILLM(LLM):
    """OpenAI Chat Completions with tool-calling.

    Uses the ``openai`` Python SDK. Picks the model from ``OPENAI_MODEL``
    (default ``gpt-4o-mini``).
    """

    name = "openai"

    def __init__(self) -> None:
        from openai import OpenAI  # local import keeps import cost off the critical path

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        kwargs: Dict[str, Any] = {"api_key": api_key}
        if base := os.environ.get("OPENAI_BASE_URL"):
            kwargs["base_url"] = base
        self.client = OpenAI(**kwargs)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def __call__(self, messages: List[Dict], tools: List[Dict]) -> LLMResponse:
        # openai v1+ expects "tool_calls" inside assistant messages, and
        # "tool" role messages for results.
        oai_messages = [_to_openai_msg(m) for m in messages]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=oai_messages,
            tools=tools or None,
            tool_choice="auto" if tools else None,
        )
        msg = resp.choices[0].message
        tool_calls: List[ToolCall] = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=args,
            ))
        return LLMResponse(text=msg.content, tool_calls=tool_calls, raw=resp)


def _to_openai_msg(m: Dict) -> Dict:
    """Translate the internal message dict to OpenAI's chat format."""
    role = m["role"]
    if role == "tool":
        return {
            "role": "tool",
            "tool_call_id": m["tool_call_id"],
            "content": m["content"],
        }
    if role == "assistant" and m.get("tool_calls"):
        return {
            "role": "assistant",
            "content": m.get("content") or "",
            "tool_calls": [{
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"]),
                },
            } for tc in m["tool_calls"]],
        }
    return {"role": role, "content": m.get("content") or ""}


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------
class AnthropicLLM(LLM):
    """Anthropic Messages API with tool-calling.

    Uses the ``anthropic`` Python SDK. Picks the model from
    ``ANTHROPIC_MODEL`` (default ``claude-3-5-sonnet-20241022``).
    """

    name = "anthropic"

    def __init__(self) -> None:
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    def __call__(self, messages: List[Dict], tools: List[Dict]) -> LLMResponse:
        # Anthropic wants system separate, and uses ``tool_result`` blocks.
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [m for m in messages if m["role"] != "system"]
        claude_msgs: List[Dict] = []
        for m in convo:
            if m["role"] == "tool":
                claude_msgs.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m["tool_call_id"],
                        "content": m["content"],
                    }],
                })
            elif m["role"] == "assistant" and m.get("tool_calls"):
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m["tool_calls"]:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["arguments"],
                    })
                claude_msgs.append({"role": "assistant", "content": blocks})
            else:
                claude_msgs.append({"role": m["role"], "content": m.get("content") or ""})
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=claude_msgs,
            tools=[{
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            } for t in tools] or None,
        )
        text_parts = [b.text for b in resp.content if b.type == "text"]
        tool_calls = [
            ToolCall(id=b.id, name=b.name, arguments=dict(b.input))
            for b in resp.content if b.type == "tool_use"
        ]
        return LLMResponse(text="\n".join(text_parts) or None, tool_calls=tool_calls, raw=resp)


# ---------------------------------------------------------------------------
# Mock LLM (deterministic, no API key)
# ---------------------------------------------------------------------------
class MockLLM(LLM):
    """Rule-based stand-in for a real LLM.

    It scans the latest user message for keywords and emits the matching
    tool calls. It exists so that the full agent loop can be smoke-tested
    without an API key. Do NOT use it for real workloads – its tool
    selection accuracy is roughly the keyword-matching baseline, far below
    the 85% target.
    """

    name = "mock"

    def __call__(self, messages: List[Dict], tools: List[Dict]) -> LLMResponse:
        # Find the latest user message.
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        tool_names = {t["function"]["name"]: t for t in tools}
        calls: List[ToolCall] = []
        text = user_msg.lower()

        # Helper: does a tool exist in the OFFERED set? If not, we can't
        # call it this turn. The MockLLM only knows the offered tools.
        def has(name: str) -> bool:
            return name in tool_names

        # Heuristic tool selection – order matters; we keep one or two calls
        # per turn so the loop converges quickly.
        if "list" in text and "file" in text and has("filesystem.list_files"):
            calls.append(ToolCall(id="c1", name="filesystem.list_files", arguments={"directory": "."}))
        elif "read" in text and has("filesystem.read_file"):
            # Match a quoted filename, or a bare .txt/.md filename in the message.
            m = (re.search(r"[\"']([^\"']+)[\"']", user_msg)
                 or re.search(r"(\S+\.(?:txt|md|json|csv))", user_msg, re.I))
            calls.append(ToolCall(id="c1", name="filesystem.read_file",
                                  arguments={"path": m.group(1) if m else "sample.txt"}))
        elif "search" in text and ("file" in text or "contain" in text or "mention" in text) and has("filesystem.search_files"):
            m = (re.search(r"[\"']([^\"']+)[\"']", user_msg)
                 or re.search(r"\babout\s+(\w+)", user_msg)
                 or re.search(r"\bfor\s+(\w+)", user_msg))
            calls.append(ToolCall(id="c1", name="filesystem.search_files",
                                  arguments={"query": (m.group(1) if m else user_msg.split()[-1])}))
        elif "write" in text and "file" in text and has("filesystem.write_file"):
            calls.append(ToolCall(id="c1", name="filesystem.write_file",
                                  arguments={"path": "output.txt", "content": "written by mock LLM"}))
        elif "table" in text and has("sqlite.list_tables"):
            calls.append(ToolCall(id="c1", name="sqlite.list_tables", arguments={}))
        elif any(w in text for w in ("calculate", "what is", "what's", "evaluate", "sqrt", "log")) \
                and any(op in user_msg for op in ("+", "*", "-", "/", "%", "**")):
            # Calculator intent. Prefer calculator.evaluate if offered;
            # otherwise fall through (the selector may have filtered it out).
            if has("calculator.evaluate"):
                # Try to pull a bare arithmetic expression out of the message.
                m = re.search(r"[\"']([^\"']+)[\"']", user_msg)
                if m:
                    expr = m.group(1)
                else:
                    # Grab everything after "what is" / "calculate" / "evaluate".
                    m = re.search(r"(?:what\s+is|what's|calculate|evaluate)\s+(.+)", user_msg, re.I)
                    expr = m.group(1).rstrip("?.").strip() if m else user_msg.rstrip("?.").strip()
                calls.append(ToolCall(id="c1", name="calculator.evaluate", arguments={"expression": expr}))
        elif any(w in text for w in ("currency", "convert")) and "usd" in text and has("custom.convert_currency"):
            calls.append(ToolCall(id="c1", name="custom.convert_currency",
                                  arguments={"amount": 100, "from_currency": "USD", "to_currency": "PKR"}))
        elif any(w in text for w in ("uuid", "id")) and has("custom.uuid_v4"):
            calls.append(ToolCall(id="c1", name="custom.uuid_v4", arguments={}))
        elif "weather" in text and has("search.search_web"):
            calls.append(ToolCall(id="c1", name="search.search_web", arguments={"query": "weather San Francisco"}))
        elif "search" in text and "web" in text and has("search.search_web"):
            calls.append(ToolCall(id="c1", name="search.search_web", arguments={"query": user_msg}))
        elif any(w in text for w in ("hash", "sha256", "md5")) and has("custom.hash_text"):
            calls.append(ToolCall(id="c1", name="custom.hash_text", arguments={"text": "hello", "algorithm": "sha256"}))
        elif any(w in text for w in ("time", "today")) and has("search.current_time"):
            calls.append(ToolCall(id="c1", name="search.current_time", arguments={"timezone": "UTC"}))

        # If the previous turn was a tool result, synthesise a final answer.
        if any(m["role"] == "tool" for m in messages[-2:]):
            last_tool = next((m for m in reversed(messages) if m["role"] == "tool"), None)
            return LLMResponse(text=f"Based on the tool result: {last_tool['content'][:500] if last_tool else ''}")

        if not calls:
            return LLMResponse(text=f"[mock LLM] I have no rule for: {user_msg!r}. Set OPENAI_API_KEY or ANTHROPIC_API_KEY for real selection.")
        return LLMResponse(tool_calls=calls)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def make_llm() -> LLM:
    """Auto-detect and return the right LLM based on env vars.

    Order: explicit mock flag > OpenAI > Anthropic > MockLLM fallback.
    """
    if os.environ.get("MCP_AGENT_USE_MOCK_LLM", "").lower() == "true":
        return MockLLM()
    if os.environ.get("OPENAI_API_KEY"):
        try:
            return OpenAILLM()
        except Exception as exc:  # noqa: BLE001
            print(f"[agent.llm] OpenAI init failed ({exc}); falling back.")
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicLLM()
        except Exception as exc:  # noqa: BLE001
            print(f"[agent.llm] Anthropic init failed ({exc}); falling back.")
    print("[agent.llm] No API key set – using MockLLM. Set OPENAI_API_KEY for real selection.")
    return MockLLM()
