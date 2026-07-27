# Hierarchical

Module: 05-agentic-patterns
Chapter: 06-hierarchical
Status: beta
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement a hierarchical multi-agent system: a top-level supervisor routes to mid-level supervisors, each of which routes to specialist agents
- Choose between flat (one supervisor) and hierarchical (supervisors of supervisors) based on team size
- Diagnose hierarchical failure modes (over-delegation, context loss across levels, slow top-level routing)
- Reason about when hierarchical becomes necessary (typically, more than 8 specialists)

## Prerequisites

- [04 Supervisor](04-supervisor.md)
- [05 Swarm](05-swarm.md)

## Conceptual foundation

A hierarchical multi-agent system has more than two levels. The top level is a supervisor that routes to mid-level supervisors. Each mid-level supervisor routes to its own set of specialists. The pattern is the agent equivalent of a human organization: a CEO routes to department heads, who route to team leads, who route to individual contributors.

The pattern becomes necessary when the specialist count exceeds what a single supervisor can route between accurately. A supervisor with 4 specialists routes well; a supervisor with 15 specialists routes poorly (the LLM cannot keep 15 capabilities in mind and select accurately). The hierarchical solution: group the 15 specialists into 3 teams of 5, with a mid-level supervisor for each team. The top-level supervisor routes to one of 3 mid-level supervisors, each of which routes to one of 5 specialists. Each routing decision is small enough to be accurate.

The trade-offs:

- Latency: hierarchical adds a routing hop. The top-level supervisor routes to a mid-level, which routes to a specialist. Two LLM calls just for routing.
- Cost: the extra routing calls cost tokens. For a 3-level hierarchy, routing cost is roughly 2x a flat supervisor.
- Context: each level can carry a different level of context. The top level sees the high-level goal; the mid-level sees the relevant team's context; the specialist sees the specific task. This is good - it prevents context bloat at the top.
- Debuggability: hierarchical is harder to debug because the decision path is longer. The trace shows the full path, but the rationale at each level must be inspected.

## Worked example

A hierarchical system for a research-and-writing task: a top-level supervisor routes to a "research" supervisor or a "writing" supervisor. The research supervisor routes to a web-researcher or a database-researcher. The writing supervisor routes to a report-writer or a summary-writer. Full code in [`examples/hierarchical_demo.py`](../examples/hierarchical_demo.py).

```python
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Leaf specialists
web_researcher = create_react_agent(llm, tools=[...], prompt="You research the web.")
db_researcher = create_react_agent(llm, tools=[...], prompt="You research the database.")
report_writer = create_react_agent(llm, tools=[...], prompt="You write reports.")
summary_writer = create_react_agent(llm, tools=[...], prompt="You write summaries.")

# Mid-level supervisors
research_team = create_supervisor(
    [web_researcher, db_researcher], llm, prompt="Route to web_researcher or db_researcher."
).compile()
writing_team = create_supervisor(
    [report_writer, summary_writer], llm, prompt="Route to report_writer or summary_writer."
).compile()

# Top-level supervisor
top = create_supervisor(
    [research_team, writing_team], llm, prompt="Route to research_team or writing_team."
).compile()
```

## Evaluation

A golden dataset of 10 tasks that require routing to different teams. The evaluator checks: (1) the top-level supervisor routed to the right team, (2) the mid-level supervisor routed to the right specialist, (3) the total routing calls did not exceed 4.

## Production notes

In production, hierarchical systems are rare - most tasks are well-served by a flat supervisor with up to 8 specialists. Hierarchical becomes necessary for large-scale systems (customer support with 20+ specialist domains, coding agents with separate teams for frontend, backend, infra, testing). The main risk: the top-level supervisor becomes a bottleneck because every request goes through it. The fix: cache routing decisions for common request types.

## Common pitfalls

- Using hierarchical when flat would do. Why: it feels more sophisticated. Fix: use flat for under 8 specialists.
- Mid-level supervisors that do too much. Why: they are agents too. Fix: mid-level supervisors only route; they do not call tools.
- Not caching top-level routing. Why: every request is unique in dev. Fix: cache common request patterns.

## Further reading

- [langgraph-supervisor: hierarchical](https://github.com/langchain-ai/langgraph-supervisor-py)
- [LangGraph multi-agent hierarchies](https://langchain-ai.github.io/langgraph/concepts/multi_agent/#hierarchical)

## Checklist

- [ ] Implement a 3-level hierarchical system (top supervisor, mid supervisor, specialists)
- [ ] Cap total routing calls at 4
- [ ] Use hierarchical only when specialist count exceeds 8
- [ ] Cache common top-level routing decisions
