# 02 - LangGraph core

Deep mastery of LangGraph's architecture and both API surfaces. By the end of this module, you can model any multi-step LLM workflow as a graph and choose the right API for the job.

## What you will learn

- The StateGraph mental model: nodes, edges, state, reducers, super-steps
- The four workflow patterns (sequential, parallel, conditional, iterative) as graphs
- The Functional API (`@entrypoint` / `@task`) and when it is preferable to StateGraph
- How to choose between the two APIs based on problem shape

## Chapters

- [01 Graph, state, edges, nodes](01-graph-state-edges-nodes.md) - the StateGraph mental model and execution semantics
- [02 Sequential workflows](02-sequential-workflows.md) - linear pipelines, the simplest graph
- [03 Parallel workflows](03-parallel-workflows.md) - fan-out and fan-in, reducers for safe state updates
- [04 Conditional workflows](04-conditional-workflows.md) - dynamic routing, conditional edges
- [05 Iterative workflows](05-iterative-workflows.md) - loops, cycles, termination conditions
- [06 Functional API](06-functional-api.md) - `@entrypoint` / `@task`, when to use it instead of StateGraph

## Prerequisites

- [01 Foundations](../01-foundations/) (all five chapters)

## Time

3 to 4 weeks at 2 to 3 hours per day.

## What is next

After this module, you are ready for [03 Agents in practice](../03-agents-in-practice/), where you will add memory, tools, human-in-the-loop, and streaming to the graphs you learned to build here.
