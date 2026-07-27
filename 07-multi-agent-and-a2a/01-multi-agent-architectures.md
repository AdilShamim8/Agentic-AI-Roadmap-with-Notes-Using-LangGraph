# Multi-agent architectures

Module: 07-multi-agent-and-a2a
Chapter: 01-multi-agent-architectures
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Choose between supervisor, swarm, hierarchical, and market-based architectures based on task structure
- Diagnose the failure modes unique to multi-agent systems (cascading errors, coordination overhead, cost explosion)
- Reason about when multi-agent is justified and when single-agent with more tools is better
- Combine multi-agent patterns (supervisor of swarms, hierarchical with reflexion)

## Prerequisites

- [05 Agentic patterns](../05-agentic-patterns/)

## Conceptual foundation

Multi-agent systems are not always better than single-agent systems. They are more complex, more expensive, and harder to debug. The justification for multi-agent is specialization: when the task requires skills that no single agent can have (because the tool list would be too long, or the system prompt would be too large), multi-agent is the right choice. When the task is single-skill, single-agent with more tools is almost always better.

The four architectures:

1. Supervisor. One router LLM delegates to N specialists. Covered in module 05. The right choice when there is a clear router structure and the specialists are distinct.

2. Swarm. Specialists hand off to each other peer-to-peer. Covered in module 05. The right choice when the specialists are peers and each knows when to hand off.

3. Hierarchical. Supervisors of supervisors. Covered in module 05. The right choice when the specialist count exceeds 8.

4. Market-based. Specialists bid on tasks; the highest bidder wins. Research-grade in 2026; not yet production-ready. Mentioned here for completeness.

The failure modes unique to multi-agent:

1. Cascading errors. One specialist produces a bad output; the next specialist builds on it; the error compounds. Single-agent has the same failure mode, but multi-agent makes it worse because each specialist has its own context and cannot sanity-check the previous specialist's output. Fix: add a validator at each handoff.

2. Coordination overhead. Each handoff is an LLM call (the supervisor or the handoff tool). A 5-specialist task has 5+ routing calls. Cost and latency add up. Fix: minimize handoffs; have each specialist do substantive work before handing off.

3. Cost explosion. Multi-agent systems have more LLM calls per request than single-agent. A 3-specialist supervisor with 5 tool calls each is 18 LLM calls (3 routing + 15 tool). The same task as a single agent with 5 tools might be 6 calls. Fix: use multi-agent only when the specialization benefit justifies the cost.

4. Context loss. Each specialist sees only the conversation up to its handoff point, plus the handoff message. If the specialist needs context from earlier in the conversation that was not in the handoff, it will fail. Fix: include full context in handoffs, or use shared state (LangGraph's StateGraph with a single state object shared across all agents).

## Worked example

No new code in this chapter - the architectures are covered in module 05. The exercise: for each of the following tasks, name the architecture and justify.

1. "Research the market, write a business plan, build a financial model." Supervisor with 3 specialists. Clear router structure, distinct skills.

2. "Coordinate 12 engineers across 4 teams to ship a feature." Hierarchical. More than 8 specialists, clear team structure.

3. "Diagnose a medical symptom by querying 5 different specialist knowledge bases." Map-reduce (each specialist evaluates independently, results are aggregated). Or supervisor with 5 specialists if the order matters.

4. "Answer a customer question that might need order lookup, refund, or knowledge base." Supervisor with 3 specialists. Clear router.

5. "Write a research paper: literature review, methodology, experiments, writing." Supervisor with 4 specialists, or plan-and-execute if the steps are sequential and dependent.

## Evaluation

The eval for multi-agent is the same as for single-agent (correctness, cost, latency), plus two multi-agent-specific metrics: handoff count (how many times did control transfer between agents) and handoff accuracy (did the right agent handle each step). Both metrics require trajectory labels in the golden dataset.

## Production notes

In production, the most common multi-agent failure is over-engineering. Teams build a 5-agent supervisor when a single agent with 5 tools would do. The cost is 3x, the latency is 2x, and the debugging is 5x harder. The rule: start with single-agent. Move to multi-agent only when you have evidence that single-agent cannot handle the task (tool selection accuracy drops below 80 percent with more than 8 tools, or the system prompt exceeds 2000 tokens).

## Common pitfalls

- Using multi-agent when single-agent would do. Why: it feels more sophisticated. Fix: start single-agent; upgrade only with evidence.
- No handoff validation. Why: it works in dev. Fix: validate each handoff; reject bad inputs.
- No handoff cap. Why: it works in dev. Fix: cap total handoffs at 10.
- Not tracking handoff count as a metric. Why: it is not in the standard dashboard. Fix: track it; it is a key cost and reliability signal.

## Further reading

- [LangGraph multi-agent](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [Anthropic: multi-agent systems](https://www.anthropic.com/research/multi-agent-research-system)

## Checklist

- [ ] Choose between supervisor, swarm, and hierarchical based on task structure
- [ ] Name the four multi-agent failure modes and their fixes
- [ ] Decide between single-agent and multi-agent based on tool count and prompt size
- [ ] Track handoff count and handoff accuracy as eval metrics
