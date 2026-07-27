# Tool integration

Module: 03-agents-in-practice
Chapter: 03-tool-integration
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Use `ToolNode` to execute tools with proper error handling
- Dynamically load tools at runtime based on user context
- Handle tool errors gracefully (retry, fallback, user-facing error)
- Wrap external APIs as LangGraph tools with proper schemas

## Prerequisites

- [01 Conversational agents](01-conversational-agents.md)

## Conceptual foundation

`ToolNode` is a prebuilt LangGraph node that takes a list of tool calls from the LLM's response, executes them in parallel, and returns the results as tool messages. It handles errors (a tool that raises an exception returns an error message to the LLM rather than crashing the graph), retries (none by default, but you can wrap), and parallelism (multiple tool calls in one LLM response are executed concurrently).

The alternative to `ToolNode` is a custom tool-execution node. You would write one when you need to: log tool calls to a custom destination, transform tool results before returning them to the LLM, or implement custom retry logic. For most cases, `ToolNode` is the right choice.

Dynamic tool loading is the pattern where the tool list depends on the user or the context. A user with admin permissions sees a different tool list than a regular user. A conversation about orders exposes order tools; a conversation about refunds exposes refund tools. The implementation: the LLM node receives the tool list as a runtime parameter, and the graph rebuilds the LLM with the right tools before each invocation. This is more expensive than a static tool list (the LLM has to be re-bound each time) but it dramatically improves tool-selection accuracy because the LLM sees only the relevant tools.

Tool error handling has three layers:

1. The tool itself catches expected errors (API timeout, invalid input, rate limit) and returns a structured error message to the LLM. The LLM can then retry with different arguments or report the error to the user.
2. The `ToolNode` catches unexpected errors (Python exceptions) and returns them as tool messages so the graph does not crash.
3. The graph has a max-retry limit; if a tool fails N times, the graph routes to an error-handling node that informs the user.

## Worked example

An agent with a custom API-wrapping tool, dynamic tool loading based on user role, and proper error handling. Full code in [`examples/tool_integration_demo.py`](../examples/tool_integration_demo.py).

```python
from typing import Annotated
from langchain_core.tools import tool, ToolException
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_openai import ChatOpenAI
import httpx

@tool
def get_order_status(order_id: str) -> str:
    """Get the status of an order. Use when the user asks about order status."""
    try:
        r = httpx.get(f"https://api.example.com/orders/{order_id}", timeout=5.0)
        r.raise_for_status()
        return f"Order {order_id}: {r.json()['status']}"
    except httpx.HTTPError as e:
        # Return the error to the LLM as a tool message, not as an exception
        return f"Error fetching order {order_id}: {e}. Ask the user to check the order ID."

@tool
def issue_refund(order_id: str, amount: float) -> str:
    """Issue a refund. Admin only. Use when the user explicitly requests a refund."""
    # In production, this would call the refund API
    return f"Refund of ${amount} issued for order {order_id}"

def build_agent(user_role: str):
    tools = [get_order_status]
    if user_role == "admin":
        tools.append(issue_refund)
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    return create_react_agent(llm, tools=tools)

# Regular user: only sees get_order_status
agent_user = build_agent("user")
# Admin: sees both tools
agent_admin = build_agent("admin")
```

## Evaluation

A golden dataset of 10 requests, each with a user role. The evaluator checks that: (1) the agent only calls tools available to the user's role, (2) tool errors are returned to the LLM as messages (not exceptions), (3) the agent does not retry a failing tool more than the limit.

## Production notes

In production, every external API call should be wrapped in a tool with a timeout and an error return. Never let an HTTP exception crash the graph. Log every tool call with its arguments, its result, and its latency - this is the data you need to diagnose production failures and to build evals. For tools with side effects (refunds, sends email, deletes data), always pair with a human-in-the-loop approval (see the next chapter).

## Common pitfalls

- Letting tool exceptions crash the graph. Why: it works when the API is up. Fix: catch exceptions in the tool and return error messages.
- Static tool lists for multi-role agents. Why: simpler. Fix: dynamic tool loading based on role.
- Not logging tool calls. Why: it works in dev. Fix: log every call with arguments, result, and latency.

## Further reading

- [LangGraph `ToolNode`](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/)
- [LangChain tools](https://python.langchain.com/docs/concepts/tools/)

## Checklist

- [ ] Use `ToolNode` in a custom StateGraph
- [ ] Wrap an external API as a tool with timeout and error handling
- [ ] Implement dynamic tool loading based on user role
- [ ] Log every tool call with arguments, result, and latency
