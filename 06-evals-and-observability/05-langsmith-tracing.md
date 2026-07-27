# LangSmith tracing

Module: 06-evals-and-observability
Chapter: 05-langsmith-tracing
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Instrument an agent with LangSmith tracing
- Read a trace and identify the failing node, tool call, or LLM invocation
- Set up dashboards for production monitoring (latency, cost, error rate, tool-call distribution)
- Configure alerts for production regressions

## Prerequisites

- [01 Why evals](01-why-evals.md)

## Conceptual foundation

LangSmith is LangChain's observability and evaluation platform. It traces every LLM call, tool call, and node execution in your agent, and presents the trace as a tree that you can inspect in a web UI. For development, it is how you debug agent failures. For production, it is how you monitor agent health.

Instrumentation is a one-liner: set the `LANGCHAIN_API_KEY` environment variable and `LANGCHAIN_TRACING_V2=true`, and LangChain automatically traces every LLM call. LangGraph traces every node execution. You do not need to add any code - the traces appear in LangSmith automatically.

A trace is a tree. The root is the agent invocation. The children are the nodes that ran. Each node's children are the LLM calls and tool calls it made. Each LLM call's children are the tokens (if streaming) or the full response. The trace shows the input and output of every node, the duration of every call, and the cost (token count x price).

Reading a trace is the core skill. The pattern:

1. Start at the root. What was the input? What was the output? If the output is wrong, the failure is somewhere in the tree.
2. Walk down the tree. Each node should produce a reasonable output given its input. The first node whose output is unreasonable is the failure point.
3. At the failure node, inspect the LLM call. What was the prompt? What was the response? Was the response wrong because the prompt was bad, or because the model failed?
4. If the model failed, check the tool calls. Did it call the right tool with the right arguments? If not, the tool description or schema needs improvement.

For production, LangSmith dashboards aggregate traces into metrics. The key dashboards:

- Latency: p50, p95, p99 over time. Alert if p95 grows by more than 20 percent week-over-week.
- Cost: total spend, spend per request, spend per user. Alert if spend per request grows.
- Error rate: percentage of requests that fail. Alert if it exceeds 1 percent.
- Tool-call distribution: which tools are called, how often. Useful for spotting tools that are never used (candidates for removal) or over-used (candidates for splitting).
- Trajectory length: number of nodes per request. Alert if it grows (a sign the agent is looping).

## Worked example

Instrumenting an agent and reading a trace. Full code in [`examples/langsmith_demo.py`](../examples/langsmith_demo.py).

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "ls__..."
os.environ["LANGCHAIN_PROJECT"] = "my-agent"

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

@tool
def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"72F, sunny in {location}"

llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent = create_react_agent(llm, tools=[get_weather])

# This invocation is automatically traced
result = agent.invoke({"messages": [{"role": "user", "content": "Weather in SF?"}]})

# The trace is visible at smith.langchain.com under the "my-agent" project
```

## Evaluation

No eval for this chapter - tracing is the tool you use to debug evals. The skill is in reading traces, which is practiced by debugging real failures.

## Production notes

In production, LangSmith tracing adds a small latency overhead (typically under 100ms per request) and a small cost (you pay for LangSmith, which is usage-based). The trade-off is worth it: without tracing, you cannot debug production failures. The alternative is to build your own tracing, which is expensive and rarely as good.

The most common production issue: tracing is too verbose. Every LLM call, every tool call, every token is traced. For a high-traffic agent, this is a lot of data. The fix: sample (trace 10 percent of requests, not 100 percent), and set retention policies (keep traces for 30 days, not forever).

## Common pitfalls

- Not enabling tracing in production. Why: it feels like overhead. Fix: enable it; the debuggability is worth the cost.
- Not setting up alerts. Why: dashboards are enough. Fix: alerts catch regressions that dashboards show only when you look.
- Not sampling for high-traffic agents. Why: trace everything. Fix: sample 10 percent; full tracing is for dev.

## Further reading

- [LangSmith documentation](https://docs.smith.langchain.com/)
- [LangSmith dashboards](https://docs.smith.langchain.com/monitoring)

## Checklist

- [ ] Instrument an agent with LangSmith tracing
- [ ] Read a trace and identify the failing node
- [ ] Set up dashboards for latency, cost, error rate, and trajectory length
- [ ] Configure alerts for production regressions
