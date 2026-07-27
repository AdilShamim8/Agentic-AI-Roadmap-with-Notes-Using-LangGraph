# Agent OS and kernels

Module: 09-emerging-topics
Chapter: 01-agent-os-and-kernels
Status: draft
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Reason about agent OS as the runtime layer for agents (analogous to an OS for processes)
- Identify the components an agent OS would provide (scheduling, memory, permissions, IPC)
- Reason about the trajectory: which components are maturing, which are still research

## Prerequisites

- [08 Production](../08-production/)

## Conceptual foundation

Today, every agent framework reimplements the same primitives: scheduling (when does an agent run), memory (how does it persist state), permissions (what can it access), IPC (how do agents communicate). These are the same primitives an operating system provides for processes. The natural trajectory is for these primitives to be extracted into a shared runtime - an "agent OS" - that frameworks build on top of.

The components an agent OS would provide:

1. Scheduling. When does an agent run? On a request? On a schedule? On an event? Today, each framework has its own answer. An agent OS would provide a unified scheduler.

2. Memory. Short-term (checkpointing) and long-term (Store). Today, LangGraph provides these within its ecosystem. An agent OS would provide them across frameworks.

3. Permissions. What tools can an agent call? What data can it access? Today, this is enforced ad-hoc in each agent. An agent OS would provide a permission system.

4. IPC. How do agents communicate? A2A is emerging as the standard. An agent OS would build on A2A and provide higher-level primitives (pub-sub, RPC, shared memory).

5. Resource accounting. How much CPU, memory, tokens, and money has an agent consumed? Today, this is tracked ad-hoc. An agent OS would track it uniformly and enforce budgets.

In 2026, agent OS is research-grade. No production agent OS exists. The closest analogues are LangGraph Platform (which provides some of these primitives within the LangGraph ecosystem) and emerging open-source projects (which aim to provide them across ecosystems). By 2027-2028, expect a production agent OS to emerge, either from a major cloud provider or from the open-source community.

## Worked example

No code - this chapter is forward-looking. The exercise: pick an agent you have built and identify which primitives it reimplements that an agent OS could provide.

## Evaluation

No eval. This chapter tracks the frontier.

## Production notes

In production (in 2026), do not wait for an agent OS. Use LangGraph Platform or self-hosted Docker, and accept that you are reimplementing some primitives. When an agent OS emerges, the migration will be incremental: replace your checkpointing with the OS's checkpointing, replace your permission system with the OS's permission system, one primitive at a time.

## Further reading

- [Agent OS discussions](https://github.com/langchain-ai/langgraph/discussions)
- [AI SDK](https://sdk.vercel.ai/docs) - Vercel's take on the agent runtime layer

## Checklist

- [ ] Name the five components an agent OS would provide
- [ ] Identify which primitives your current agent reimplements
- [ ] Reason about the trajectory of agent OS over the next 2 years
