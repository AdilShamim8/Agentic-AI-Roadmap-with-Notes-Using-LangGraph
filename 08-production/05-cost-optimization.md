# Cost optimization

Module: 08-production
Chapter: 05-cost-optimization
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement model routing (cheap model for simple, expensive for complex)
- Implement token budgeting (cap tokens per request, per session, per user)
- Implement semantic caching (cache tool results and LLM responses)
- Reason about the cost-quality trade-off and set cost budgets per agent

## Prerequisites

- [06 Cost and latency](../06-evals-and-observability/06-cost-and-latency.md)
- [04 Checkpointing and durability](04-checkpointing-and-durability.md)

## Conceptual foundation

Cost optimization in production agents is not a one-time exercise; it is a continuous discipline. Agents drift toward higher cost over time: conversations get longer, the eval suite grows, new tools are added. Without active cost management, a $0.03-per-request agent becomes a $0.30-per-request agent in six months.

The three optimization techniques (covered in module 06, deepened here for production):

1. Model routing. A cheap classifier LLM call decides whether the request is "simple" or "complex." Simple requests go to a cheap model (GPT-4o-mini, Claude Haiku); complex requests go to an expensive model (GPT-4o, Claude Sonnet). Typical cost reduction: 40-60 percent with no quality loss.

2. Token budgeting. Every request has a maximum token budget (input + output). If the agent exceeds the budget, it is terminated and a fallback response is returned. This prevents runaway costs from confused agents (the agent that calls 20 tools and produces a 5000-token response). The budget is set per agent based on the eval distribution: take the p99 token count from the eval, add 20 percent, that is the budget.

3. Semantic caching. Cache tool results (and sometimes LLM responses) by semantic similarity. If `get_weather("San Francisco")` was called 5 minutes ago, return the cached result for `get_weather("SF")`. The cache has a TTL (weather: 10 minutes; exchange rates: 1 hour; document lookups: forever). Typical cost reduction for tool-heavy agents: 20-40 percent.

The cost-quality trade-off: every cost optimization has a quality risk. Model routing can send a complex request to a cheap model and get a bad answer. Token budgeting can cut off an agent that was about to produce a good answer. Semantic caching can return a stale result. The mitigation: every optimization is gated by the eval suite. If the eval score drops when you enable an optimization, the optimization is wrong; tune it or revert.

## Worked example

A production agent with all three optimizations. Full code in [`examples/cost_optimization_production_demo.py`](../examples/cost_optimization_production_demo.py).

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
import hashlib
import time

# Semantic cache (in production, use Redis)
_cache = {}

def cache_key(tool_name: str, args: dict, ttl_buckets: dict) -> str:
    raw = f"{tool_name}:{sorted(args.items())}"
    return hashlib.md5(raw.encode()).hexdigest()

@tool
def get_weather(location: str) -> str:
    """Get weather. Cached for 10 minutes."""
    key = cache_key("weather", {"location": location})
    if key in _cache and time.time() - _cache[key][1] < 600:
        return _cache[key][0]
    result = f"72F, sunny in {location}"  # call real API in production
    _cache[key] = (result, time.time())
    return result

def route_model(question: str) -> ChatOpenAI:
    router = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    difficulty = router.invoke(f"Is this question 'simple' or 'complex'? Reply one word.\n\n{question}").content.strip()
    if difficulty == "simple":
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return ChatOpenAI(model="gpt-4o", temperature=0)

def agent_with_optimizations(question: str):
    llm = route_model(question)
    agent = create_react_agent(llm, tools=[get_weather])
    # In production, also set a recursion_limit and a token budget
    return agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 8},
    )
```

## Evaluation

Run the eval suite with and without each optimization. The eval report should show: cost per row (with and without), quality score (with and without). An optimization that reduces cost by 50 percent but drops quality by 5 percent is a judgment call; an optimization that reduces cost by 50 percent with no quality loss is a clear win.

## Production notes

In production, set a monthly cost budget per agent. Track spend daily; alert if the run-rate exceeds the budget. When the budget is exceeded, the first response is to increase optimization (more aggressive routing, lower TTLs on the cache, tighter token budgets), not to increase the budget. Only increase the budget when the optimizations have been exhausted and the agent is still over budget.

The most common production failure: the cache returns stale data. The user asks for the weather, the cache returns yesterday's weather. The fix: set TTLs based on the data's volatility, and add a "last updated" timestamp to cached results so the user (and the LLM) can see freshness.

## Common pitfalls

- Optimizing without measuring quality. Why: cost goes down, so it must be good. Fix: gate every optimization with the eval suite.
- Too-aggressive routing. Why: it cuts cost more. Fix: tune the router; if complex requests are misclassified as simple, quality drops.
- Cache TTLs too long. Why: it improves hit rate. Fix: set TTLs based on data volatility; stale data is worse than a cache miss.

## Further reading

- [LangSmith cost tracking](https://docs.smith.langchain.com/monitoring/cost)
- [LangChain model routing](https://python.langchain.com/docs/how_to/routing/)

## Checklist

- [ ] Implement model routing with a cheap classifier
- [ ] Set a per-request token budget based on the eval p99
- [ ] Implement semantic caching with per-tool TTLs
- [ ] Gate every optimization with the eval suite
