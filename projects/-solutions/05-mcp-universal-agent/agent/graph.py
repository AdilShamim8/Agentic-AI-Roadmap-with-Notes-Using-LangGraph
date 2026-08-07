"""Stage 4 & 5 of the agent loop: execution + synthesis, orchestrated by
LangGraph.

The graph is a tiny state machine:

    +----------------+      +------------+      +-----------+
    | select_tools   | ---> | call_llm   | ---> | execute   |
    +----------------+      +------------+      +-----------+
                                  ^                   |
                                  |                   v
                                  +----- if tool -----+
                                        calls remain
                                  |
                                  v
                              synthesize (final answer)

State is a :class:`AgentState` dict with:

- ``messages``       – the running chat log (system, user, assistant, tool)
- ``user_goal``      – the original user goal, kept for retrieval queries
- ``iteration``      – current loop iteration (capped by ``MAX_ITERATIONS``)
- ``trace``          – append-only list of selection rationales + tool calls
                       (used by the eval framework to score trajectory)
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from .discovery import DiscoveryResult, ToolInfo, discover_servers
from .llm import LLM, LLMResponse, ToolCall, make_llm
from .tool_selector import SelectionResult, ToolSelector


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class AgentState(TypedDict, total=False):
    """Mutable state passed between graph nodes.

    ``messages`` uses LangGraph's ``add_messages`` reducer so each node can
    return just the *new* messages and the framework appends them.

    ``_offered_tools`` and ``_llm_response`` are internal scratch fields that
    pass data between the ``select`` -> ``llm`` -> ``execute`` nodes within
    a single iteration. They ARE part of the schema (not just stashed
    ad-hoc) because LangGraph only preserves keys that appear in the
    TypedDict.
    """

    messages: Annotated[List[Dict], add_messages]
    user_goal: str
    iteration: int
    trace: List[Dict]
    final_answer: Optional[str]
    # Internal scratch (not user-facing).
    _offered_tools: List[Dict]
    _llm_response: Any


# ---------------------------------------------------------------------------
# System prompt – shared by all strategies.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a universal MCP agent. You accomplish the user's goal by calling
tools exposed by MCP servers.

Rules:
1. You may ONLY call tools from the list provided in this turn. Tool names
   are fully-qualified: "<server>.<tool>".
2. If the answer is already in the conversation, do NOT call a tool – just
   answer.
3. Call at most 2 tools per turn. If you need more, explain why.
4. After tool results come back, synthesise a concise final answer that
   directly addresses the user's goal. Quote specific values from the tool
   results when relevant.
5. If a tool fails, explain the failure to the user and either retry with
   corrected arguments or pick a different tool. Do not silently fail.
"""


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------
@dataclass
class GraphContext:
    """Holds the long-lived objects the graph nodes need access to.

    LangGraph nodes are pure functions of state, so we close over the
    context via functools.partial when building the graph.
    """

    discovery: DiscoveryResult
    llm: LLM
    selector: ToolSelector
    max_iterations: int = int(os.environ.get("MCP_AGENT_MAX_ITERATIONS", "8"))
    tools_by_name: Dict[str, ToolInfo] = field(default_factory=dict)
    sessions_by_server: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for t in self.discovery.tools:
            self.tools_by_name[t.name] = t
        for s in self.discovery.servers:
            self.sessions_by_server[s.name] = s.session


def _select_tools_node(ctx: GraphContext, state: AgentState) -> Dict:
    """Pick which tools the LLM sees this turn (stage 3)."""
    user_goal = state.get("user_goal", "")
    history = state.get("messages", [])
    sel: SelectionResult = ctx.selector.select(user_goal, history)
    trace = list(state.get("trace") or [])
    trace.append({
        "step": "select",
        "iteration": state.get("iteration", 0),
        "strategy": sel.strategy,
        "rationale": sel.rationale,
        "tools_offered": [t["function"]["name"] for t in sel.tools],
    })
    # Stash the offered tools on state so the LLM node can use them.
    return {
        "trace": trace,
        "_offered_tools": sel.tools,  # type: ignore[call-overload]
    }


def _call_llm_node(ctx: GraphContext, state: AgentState) -> Dict:
    """Ask the LLM what to do next, given the offered tools."""
    tools = state.get("_offered_tools") or []  # type: ignore[call-overload]
    # Normalise messages: LangGraph's add_messages reducer converts dicts to
    # BaseMessage objects, but our LLM providers expect dicts.
    messages: List[Dict] = _normalise_messages(state.get("messages") or [])
    # Ensure system prompt is present.
    if not any(m.get("role") == "system" for m in messages):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    resp: LLMResponse = ctx.llm(messages, tools)
    assistant_msg: Dict[str, Any] = {"role": "assistant", "content": resp.text or ""}
    if resp.tool_calls:
        # langchain-core's add_messages reducer validates tool_calls – they
        # MUST use the {"name", "args", "id", "type": "tool_call"} shape
        # (NOT "arguments").  We keep both shapes in sync: the dict stored
        # in the message uses langchain's format; _normalise_messages
        # translates back to OpenAI format when handing to the LLM.
        assistant_msg["tool_calls"] = [
            {"name": tc.name, "args": tc.arguments, "id": tc.id, "type": "tool_call"}
            for tc in resp.tool_calls
        ]
    trace = list(state.get("trace") or [])
    trace.append({
        "step": "llm",
        "iteration": state.get("iteration", 0),
        "text": resp.text,
        "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                       for tc in resp.tool_calls],
        "provider": ctx.llm.name,
    })
    return {
        "messages": [assistant_msg],
        "trace": trace,
        "_llm_response": resp,  # type: ignore[call-overload]
    }


async def _execute_tools_node(ctx: GraphContext, state: AgentState) -> Dict:
    """Run every tool call the LLM requested (stage 4)."""
    resp: LLMResponse = state["_llm_response"]  # type: ignore[index]
    new_messages: List[Dict] = []
    trace = list(state.get("trace") or [])
    for tc in resp.tool_calls:
        result, ok = await _invoke_tool(ctx, tc)
        new_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result) if not isinstance(result, str) else result,
        })
        trace.append({
            "step": "tool",
            "tool": tc.name,
            "arguments": tc.arguments,
            "ok": ok,
            "result_preview": (str(result)[:300]),
        })
    iteration = state.get("iteration", 0) + 1
    return {"messages": new_messages, "trace": trace, "iteration": iteration}


async def _invoke_tool(ctx: GraphContext, tc: ToolCall) -> tuple[Any, bool]:
    """Dispatch a tool call to the right MCP server session."""
    if tc.name not in ctx.tools_by_name:
        return {"error": f"Unknown tool: {tc.name}"}, False
    info: ToolInfo = ctx.tools_by_name[tc.name]
    session = ctx.sessions_by_server.get(info.server)
    if session is None:
        return {"error": f"Server not connected: {info.server}"}, False
    try:
        # MCP tool args are passed as a flat kwargs dict; the JSON schema
        # guarantees the keys match the FastMCP signature.
        result = await session.call_tool(info.tool_name, arguments=tc.arguments)
        # FastMCP returns CallToolResult with .content (list of TextContent).
        texts = []
        for block in (result.content or []):
            if hasattr(block, "text"):
                texts.append(block.text)
            else:
                texts.append(str(block))
        # Try to parse as JSON for downstream consumers; fall back to string.
        joined = "\n".join(texts)
        try:
            return json.loads(joined), True
        except json.JSONDecodeError:
            return joined, True
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}, False


def _should_continue(ctx: GraphContext, state: AgentState) -> str:
    """Router: keep looping if the LLM asked for tools, else synthesise."""
    resp: Optional[LLMResponse] = state.get("_llm_response")  # type: ignore[assignment]
    if resp and resp.tool_calls:
        if state.get("iteration", 0) >= ctx.max_iterations:
            return "synthesize"
        return "execute"
    return "synthesize"


def _synthesize_node(ctx: GraphContext, state: AgentState) -> Dict:
    """Stage 5: produce a final answer if the LLM didn't already."""
    resp: Optional[LLMResponse] = state.get("_llm_response")  # type: ignore[assignment]
    if resp and resp.text:
        return {"final_answer": resp.text}
    # LLM produced no text and no tool calls – ask it to summarise.
    messages = _normalise_messages(state.get("messages") or [])
    messages.append({
        "role": "user",
        "content": "Summarise the tool results above into a final answer for the original goal.",
    })
    final = ctx.llm(messages, tools=[])
    return {"final_answer": final.text or "(no final answer produced)"}


def _normalise_messages(messages: List) -> List[Dict]:
    """Convert LangChain ``BaseMessage`` objects back into plain dicts.

    LangGraph's ``add_messages`` reducer stores messages as BaseMessage
    instances; our LLM providers expect dicts. We translate the
    ``AIMessage.tool_calls`` attribute (namedtuples with ``.name``, ``.args``,
    ``.id``) back into the OpenAI ``tool_calls`` shape (dicts with
    ``id``, ``name``, ``arguments``) so the LLM providers can consume them.
    """
    out: List[Dict] = []
    for m in messages or []:
        if isinstance(m, dict):
            out.append(m)
            continue
        t = getattr(m, "type", "") or ""
        role = {"human": "user", "ai": "assistant"}.get(t, t)
        entry: Dict[str, Any] = {"role": role, "content": getattr(m, "content", "") or ""}
        # Tool messages carry the tool_call_id they're responding to.
        if t == "tool":
            tc_id = getattr(m, "tool_call_id", None)
            if tc_id:
                entry["tool_call_id"] = tc_id
        # AIMessages may carry .tool_calls (list of ToolCall namedtuples).
        tcs = getattr(m, "tool_calls", None) or []
        if tcs:
            entry["tool_calls"] = [
                {"id": tc.get("id") if isinstance(tc, dict) else tc.id,
                 "name": tc.get("name") if isinstance(tc, dict) else tc.name,
                 "arguments": tc.get("args") if isinstance(tc, dict) else tc.args}
                for tc in tcs
            ]
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_graph(ctx: GraphContext):
    """Wire up the LangGraph state machine.

    Returns a compiled graph that can be ``.invoke()``-ed with an initial
    :class:`AgentState`.
    """
    import functools

    g = StateGraph(AgentState)
    g.add_node("select", functools.partial(_select_tools_node, ctx))
    g.add_node("llm", functools.partial(_call_llm_node, ctx))
    g.add_node("execute", functools.partial(_execute_tools_node, ctx))
    g.add_node("synthesize", functools.partial(_synthesize_node, ctx))

    g.set_entry_point("select")
    g.add_edge("select", "llm")
    g.add_conditional_edges(
        "llm",
        functools.partial(_should_continue, ctx),
        {"execute": "execute", "synthesize": "synthesize"},
    )
    g.add_edge("execute", "select")  # loop back for the next turn
    g.add_edge("synthesize", END)
    return g.compile()


# ---------------------------------------------------------------------------
# High-level runner – what the CLI / evals call.
# ---------------------------------------------------------------------------
async def run_agent(
    user_goal: str,
    registry_path: str = "registry.json",
    only: Optional[List[str]] = None,
    llm: Optional[LLM] = None,
    selection_strategy: Optional[str] = None,
    verbose: bool = False,
) -> Dict:
    """Run the full agent loop against ``user_goal``.

    Returns a dict with keys: ``answer``, ``trace``, ``iterations``,
    ``provider``, ``strategy``. Caller can serialise this to JSON for evals.

    Args:
        user_goal: The natural-language goal to accomplish.
        registry_path: Path to ``registry.json``.
        only: Optional list of server names to limit discovery to.
        llm: Optional LLM instance (defaults to :func:`make_llm`).
        selection_strategy: Override the env-configured strategy.
        verbose: Print trace events to stdout.
    """
    llm = llm or make_llm()
    async with discover_servers(registry_path, only=only) as discovery:
        selector = ToolSelector(
            all_tools=discovery.tools,
            strategy=selection_strategy,
            llm=llm,
        )
        ctx = GraphContext(discovery=discovery, llm=llm, selector=selector)
        graph = build_graph(ctx)
        initial: AgentState = {
            "messages": [{"role": "user", "content": user_goal}],
            "user_goal": user_goal,
            "iteration": 0,
            "trace": [],
        }
        if verbose:
            print(f"[agent] provider={llm.name} strategy={selector.strategy} tools={len(discovery.tools)}")
        final = await graph.ainvoke(initial)
        if verbose:
            for step in final.get("trace", []):
                txt = step.get("text") or ""
                detail = step.get("rationale") or step.get("tool") or txt[:80]
                print(f"[trace] {step.get('step')}: {detail}")
        return {
            "answer": final.get("final_answer") or "",
            "trace": final.get("trace") or [],
            "iterations": final.get("iteration", 0),
            "provider": llm.name,
            "strategy": selector.strategy,
            "tools_offered_total": len(discovery.tools),
        }
