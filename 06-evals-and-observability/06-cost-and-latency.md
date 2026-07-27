# Cost and latency

Module: 06-evals-and-observability
Chapter: 06-cost-and-latency
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Track per-request cost (input tokens, output tokens, tool calls) and aggregate it
- Track per-request latency (time to first token, total time, time per tool call)
- Implement cost optimization: model routing, token budgeting, semantic caching
- Set cost and latency budgets and alert when they are exceeded

## Prerequisites

- [05 LangSmith tracing](05-langsmith-tracing.md)

## Conceptual foundation

Cost and latency are quality signals, not just budget concerns. An agent that costs $1 per request is probably doing something wrong (too many tool calls, no caching, no model routing). An agent with 30-second p95 latency is probably doing something wrong (sequential when it could be parallel, no streaming, slow tools). Tracking cost and latency is how you catch these issues before users do.

The metrics to track:

1. Per-request cost. The sum of all LLM call costs in the request. Each LLM call's cost is `input_tokens * input_price + output_tokens * output_price`. Track the distribution (p50, p95, p99), not just the average.

2. Per-request latency. The wall-clock time from request to response. Break it down: time to first token, time in LLM calls, time in tool calls, time in graph overhead. The breakdown tells you where to optimize.

3. Tool-call count. The number of tool calls per request. More tool calls means more cost and more latency. Track the distribution.

4. Token efficiency. Output tokens per request (you pay for output). Track whether the agent is verbose (a sign of a prompt issue).

The three optimization techniques:

1. Model routing. Route easy requests to a cheap model (GPT-4o-mini, Claude Haiku) and hard requests to an expensive model (GPT-4o, Claude Sonnet). The router is a cheap LLM call that classifies the request difficulty. This typically reduces cost by 40-60 percent with no quality loss.

2. Token budgeting. Set a maximum number of tokens per request (input + output). If the agent exceeds the budget, terminate it and return a fallback response. This prevents runaway costs from confused agents.

3. Semantic caching. Cache tool results (and sometimes LLM responses) by semantic similarity. If the agent calls `get_weather("San Francisco")` and the same call was made 5 minutes ago, return the cached result. This is most effective for tools with stable results (weather, exchange rates, document lookups).

## Worked example

A cost-tracking wrapper and a model router. Full code in [`examples/cost_optimization_demo.py`](../examples/cost_optimization_demo.py).

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Model router: cheap model for simple questions, expensive for complex
ROUTER_PROMPT = """Classify this question as 'simple' or 'complex'.
- simple: factual lookup, math, basic question
- complex: multi-step reasoning, research, analysis
Reply with one word.

Question: {question}"""

def route_model(question: str) -> ChatOpenAI:
    router = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    difficulty = router.invoke(ROUTER_PROMPT.format(question=question)).content.strip()
    if difficulty == "simple":
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return ChatOpenAI(model="gpt-4o", temperature=0)

@tool
def calculator(expr: str) -> str:
    """Evaluate a math expression."""
    try: return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e: return f"Error: {e}"

def agent_with_routing(question: str):
    llm = route_model(question)
    agent = create_react_agent(llm, tools=[calculator])
    return agent.invoke({"messages": [{"role": "user", "content": question}]})
```

## Evaluation

Track the cost and latency of every eval run. The eval report should include: total cost, cost per row, p50/p95 latency, average tool-call count. Compare these across eval runs to spot regressions.

## Production notes

In production, cost and latency budgets are set by the business. "The agent must cost less than $0.05 per request and respond in under 5 seconds p95." These budgets drive engineering decisions: which model to use, how many tool calls to allow, whether to cache. Track the budgets in the dashboard and alert when they are exceeded.

The most common production failure: cost grows over time as conversations get longer (more context = more input tokens per call). The fix: implement summarization (chapter 03) to cap conversation length, and set a per-request token budget.

## Common pitfalls

- Not tracking cost per request. Why: the bill arrives monthly. Fix: track per request; you cannot optimize what you do not measure.
- Using the most expensive model for everything. Why: it is the best. Fix: route; most requests do not need the best model.
- Not setting a token budget. Why: it works in dev. Fix: set a budget; runaway costs are a real production incident.
- Not caching tool results. Why: caching is hard. Fix: cache stable results (weather, lookups); the savings are large.

## Further reading

- [LangSmith cost tracking](https://docs.smith.langchain.com/monitoring/cost)
- [LangChain model routing](https://python.langchain.com/docs/how_to/routing/)

## Checklist

- [ ] Track per-request cost and latency, with p50/p95/p99 distributions
- [ ] Implement model routing (cheap model for simple, expensive for complex)
- [ ] Set a per-request token budget and handle budget exhaustion
- [ ] Implement semantic caching for stable tool results
