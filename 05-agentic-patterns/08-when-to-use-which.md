# When to use which

Module: 05-agentic-patterns
Chapter: 08-when-to-use-which
Status: stable
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Given a task, choose the right pattern (or combination) with reasons
- Recognize the signals that indicate each pattern (number of steps, tool count, multi-skill, batch size)
- Combine patterns (supervisor of reflexion agents, map-reduce of plan-and-execute)
- Know when not to use an agent at all (use a chain or a workflow)

## Prerequisites

- All chapters in this module

## Conceptual foundation

This chapter is the decision guide. It distills the previous seven chapters into a set of rules you can apply in 30 seconds.

The decision tree, in order:

1. Is the task a fixed sequence of LLM calls with no routing? Use a chain. Not an agent.

2. Is the task a fixed sequence with conditional routing? Use a workflow (StateGraph with conditional edges, no cycles). Not an agent.

3. Is the task a single LLM call with tools, where the order of tool calls depends on results? Use ReAct. This is the default agent pattern.

4. Is the task complex enough that ReAct loses track (5+ steps, or the LLM forgets the goal mid-task)? Use plan-and-execute.

5. Is the failure mode such that the agent makes a specific, identifiable mistake that it could learn from? Add reflexion on top of ReAct or plan-and-execute.

6. Does the task require multiple skills that no single agent has (research + analysis + writing)? Use a supervisor with specialist agents.

7. Are the specialists peers with no clear hierarchy, and does each know when to hand off? Use swarm instead of supervisor.

8. Are there more than 8 specialists? Use a hierarchical supervisor.

9. Is the task a batch of independent items? Use map-reduce.

10. Is the task none of the above? You probably need a custom graph. Start from the closest pattern and modify.

Combinations:

- Supervisor of reflexion agents. Each specialist is a reflexion agent that learns from its mistakes. Use when specialists handle repeated task types.

- Map-reduce of plan-and-execute. Each item in the batch is complex enough to need a plan. Use when the batch items are not trivial.

- Supervisor with a reflexion loop at the top. The supervisor reflects on its routing decisions and improves over time. Use in long-running systems.

Anti-patterns:

- Using an agent when a chain would do. The most common mistake. Costs more, fails more, harder to debug.

- Using a supervisor for a single-skill task. The supervisor adds a routing call for no benefit.

- Using reflexion for a task where failures are random (not identifiable mistakes). Reflexion only helps when the failure has a specific cause the LLM can identify and fix.

- Using hierarchical for under 8 specialists. The extra level adds latency and cost without improving routing accuracy.

## Worked example

No code. The exercise: for each of the following tasks, name the pattern and justify the choice.

1. "Summarize this document in 3 bullets." Chain. One LLM call, no routing, no tools.

2. "Answer the user's question, using web search and a calculator as needed." ReAct. Multiple tool calls, order depends on results.

3. "Research the history of AI, write a 5-section report, and translate it to French." Supervisor (research, writing, translation specialists). Multi-skill, clear router structure.

4. "Review each of these 50 pull requests and flag the ones with security issues." Map-reduce. Batch of independent items.

5. "Write code that passes this test suite, retrying until it passes or 3 attempts are exhausted." Reflexion. Identifiable failures (test failures), learning across attempts.

6. "Manage a customer support conversation that might need order lookup, refund processing, escalation, and knowledge base search." Supervisor with 4 specialists. Multi-skill, clear router.

7. "Coordinate 12 specialists across frontend, backend, infra, and QA for a complex feature build." Hierarchical. More than 8 specialists, clear team structure.

## Evaluation

The eval for this chapter is the exercise above. The "right" answers are not unique - the goal is to be able to defend a choice, not to match a specific pattern.

## Production notes

In production, the pattern choice is not permanent. Teams often start with ReAct, hit its limits, upgrade to plan-and-execute, then add a supervisor when the task scope grows. The architecture should evolve with the task. Do not over-engineer the first version; do not under-engineer the third version.

The most common production regret: starting with a supervisor when ReAct would have been enough. The supervisor adds a routing LLM call to every request, which adds latency and cost. If the task is single-skill, the supervisor is overhead. Add the supervisor when the task actually becomes multi-skill.

## Common pitfalls

- Defaulting to the most sophisticated pattern. Why: it feels more capable. Fix: start with the simplest pattern that works; upgrade only when you hit its limits.
- Not upgrading when you hit limits. Why: the simple pattern "mostly" works. Fix: if you are adding workarounds to a pattern, it is time to upgrade.
- Combining patterns too eagerly. Why: combinations feel powerful. Fix: combine only when the combination solves a problem a single pattern cannot.

## Further reading

- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) - the essay that motivates the "start simple" principle
- All chapters in this module

## Checklist

- [ ] Given a task, choose the right pattern in under 30 seconds with reasons
- [ ] Recognize the signals for each pattern (step count, tool count, multi-skill, batch)
- [ ] Combine patterns when a single pattern is insufficient
- [ ] Recognize when not to use an agent at all
