# Continuous improvement

Module: 08-production
Chapter: 07-continuous-improvement
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement feedback loops (explicit thumbs-up/down and implicit re-asks)
- A/B test agent versions (different prompts, different models)
- Implement online evals (evaluate production traffic in real time)
- Version agents (track which version produced which output, for rollback)

## Prerequisites

- [06 Governance and safety](06-governance-and-safety.md)

## Conceptual foundation

An agent in production is not done; it is just started. Continuous improvement is the discipline of measuring the agent in production, identifying failures, and shipping improvements. Without it, the agent degrades over time (model updates, user behavior shifts, the world changes) and nobody notices until the complaints pile up.

The four components of continuous improvement:

1. Feedback loops. Collect explicit feedback (thumbs up/down, ratings, free-text comments) and implicit feedback (did the user re-ask the same question? did the user abandon the conversation? did the user escalate to a human?). Implicit feedback is more plentiful than explicit; both are valuable.

2. A/B testing. Run two versions of the agent (different prompts, different models, different tool sets) on a fraction of traffic. Compare the eval scores (and the feedback) between versions. Promote the winner. The infrastructure: route a percentage of requests to each version, tag each request with the version, and aggregate metrics by version.

3. Online evals. Evaluate production traffic in real time, not just the golden dataset. Sample 1-5 percent of production requests, run the LLM-as-judge on them, and track the score over time. Online evals catch distribution shift (the agent's production inputs drift from the golden dataset) and model-update regressions (the underlying model changes and quality drops).

4. Agent versioning. Every change to the agent (prompt, model, tools, graph structure) is a new version. Each request is tagged with the agent version. If a version regresses, you can roll back to the previous version. Versions are semantic (major for breaking changes, minor for improvements, patch for fixes).

## Worked example

An A/B test infrastructure for two agent versions. Full code in [`examples/continuous_improvement_demo.py`](../examples/continuous_improvement_demo.py).

```python
import random
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

@tool
def search(query: str) -> str:
    """Search."""
    return f"[Results: {query}]"

# Version A: GPT-4o, concise prompt
agent_a = create_react_agent(
    ChatOpenAI(model="gpt-4o", temperature=0),
    tools=[search],
    prompt="Answer concisely.",
)

# Version B: GPT-4o, detailed prompt
agent_b = create_react_agent(
    ChatOpenAI(model="gpt-4o", temperature=0),
    tools=[search],
    prompt="Answer thoroughly. Use multiple sources. Cite your sources.",
)

def route_request(message: str, version_weights: dict = {"a": 0.5, "b": 0.5}):
    version = random.choices(list(version_weights.keys()), weights=list(version_weights.values()))[0]
    agent = agent_a if version == "a" else agent_b
    result = agent.invoke({"messages": [{"role": "user", "content": message}]})
    # Tag the result with the version for later analysis
    return {"version": version, "response": result["messages"][-1].content}
```

## Evaluation

The continuous improvement loop is itself evaluated: how quickly does a regression get caught, how often does an A/B test produce a clear winner, how stable are the online eval scores? These meta-metrics tell you whether the improvement loop is working.

## Production notes

In production, the continuous improvement loop runs on a weekly cadence: Monday, review the previous week's feedback and online evals; Tuesday, identify the top failure; Wednesday-Thursday, implement a fix; Friday, A/B test the fix. The next Monday, promote or revert. This cadence keeps the agent improving without overwhelming the team.

The most common production failure: feedback is collected but never acted on. The dashboard shows a 70 percent thumbs-up rate, but nobody investigates the 30 percent. The fix: assign an owner to the feedback review, make it a recurring meeting, and track the rate of fixes shipped per week.

## Common pitfalls

- Collecting feedback but not acting on it. Why: "we will look at it later." Fix: assign an owner; make it a weekly meeting.
- A/B testing without enough traffic. Why: "the winner looked better." Fix: use statistical significance; small samples produce noise.
- No online evals. Why: the golden dataset is enough. Fix: online evals catch distribution shift; the golden dataset does not.
- No rollback plan. Why: "the new version is better." Fix: version everything; roll back if the new version regresses.

## Further reading

- [LangSmith online evals](https://docs.smith.langchain.com/monitoring/online-evaluations)
- [LangSmith feedback](https://docs.smith.langchain.com/monitoring/feedback)

## Checklist

- [ ] Implement explicit and implicit feedback collection
- [ ] Set up A/B testing infrastructure for agent versions
- [ ] Implement online evals on a sample of production traffic
- [ ] Version every agent change and tag requests with the version
