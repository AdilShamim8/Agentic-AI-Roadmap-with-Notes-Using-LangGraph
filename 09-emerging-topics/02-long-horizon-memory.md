# Long-horizon memory

Module: 09-emerging-topics
Chapter: 02-long-horizon-memory
Status: draft
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Define the long-horizon memory problem (agents that run for hours or days need memory that survives across sessions)
- Distinguish the three memory types (semantic, episodic, procedural) and their roles
- Reason about the current best answers (the LangGraph Store, vector retrieval, graph memory)
- Identify the open problems (forgetting, consolidation, cross-user memory)

## Prerequisites

- [03 Persistence and memory](../03-agents-in-practice/02-persistence-and-memory.md)

## Conceptual foundation

Long-horizon memory is the open problem in agents. An agent that runs for 5 minutes can keep its state in the context window. An agent that runs for 5 days cannot - the context window fills, and the agent forgets earlier context. The agent needs memory that persists across sessions, that can be retrieved efficiently, and that captures not just facts but relationships, sequences, and skills.

The three memory types, borrowed from cognitive science:

1. Semantic memory. Facts and concepts. "The user's name is Alice. Alice works at Acme Corp. Acme Corp's refund policy is 30 days." Stored as a knowledge graph or a vector store. Retrieved by relevance to the current task.

2. Episodic memory. Specific events in time. "On Tuesday, the user asked about order ACME-123. I refunded it. The user was happy." Stored as a sequence of events with timestamps. Retrieved by temporal proximity or by similarity to the current situation.

3. Procedural memory. Skills and procedures. "When a user asks for a refund, first check the order status, then verify the refund policy, then issue the refund." Stored as procedures or policies. Retrieved when the situation matches the procedure's trigger.

Today (2026), most agents have only semantic memory (the Store, vector retrieval). Episodic and procedural memory are research-grade. The LangGraph Store can be extended to support all three, but the patterns are not yet standardized.

The open problems:

- Forgetting. Memory grows unboundedly. The agent must forget irrelevant memories, but determining irrelevance is hard. The current best answer: time-based decay (older memories are less likely to be retrieved) and importance-based pruning (low-importance memories are deleted first).

- Consolidation. Raw experience (every conversation turn) is too granular for long-term storage. The agent must consolidate experiences into higher-level memories. The current best answer: a periodic consolidation job that summarizes old conversations into semantic facts.

- Cross-user memory. Some memories are user-specific (their preferences); some are shared (the company's policies). The agent must distinguish and not leak user-specific memories across users.

## Worked example

No code - this chapter is forward-looking. The exercise: design a memory architecture for a long-horizon agent (a personal assistant that runs for months). What goes in semantic, episodic, and procedural memory? How is forgetting handled? How is consolidation done?

## Evaluation

No eval. This chapter tracks the frontier.

## Production notes

In production (in 2026), use the LangGraph Store for semantic memory. Add a consolidation job that runs nightly to extract facts from the day's conversations. For episodic and procedural memory, you are on your own - the patterns are not yet standardized, and you will be doing research-grade work.

Watch this space. Long-horizon memory is the most active research area in agentic AI, and the patterns that emerge in 2026-2027 will define the next generation of agents.

## Further reading

- [Generative Agents paper](https://arxiv.org/abs/2304.03442) - the canonical reference for long-horizon agent memory
- [MemGPT](https://arxiv.org/abs/2310.08560) - OS-inspired memory management for LLMs
- [LangGraph Store](https://langchain-ai.github.io/langgraph/concepts/memory/)

## Checklist

- [ ] Distinguish semantic, episodic, and procedural memory
- [ ] Design a memory architecture for a long-horizon agent
- [ ] Reason about forgetting, consolidation, and cross-user memory
