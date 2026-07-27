# From data engineer to agentic AI engineer

Pipelines and persistence map directly. The new skill is orchestration - LangGraph and the agent patterns.

## What you already have

- Data pipelines - ingestion, transformation, delivery (ETL/ELT)
- SQL and database design
- Python, possibly Scala or Java
- Workflow orchestration - Airflow, Dagster, Prefect
- Cloud platforms and infrastructure
- Distributed systems - Spark, Kafka, message queues
- Data modeling and schema design

## What you need to learn

- LLM fundamentals - you have not worked with probabilistic systems before
- Prompt engineering and prompt versioning
- LangGraph - it is a workflow orchestrator, which you know, but with LLM-specific patterns
- Agent patterns and their failure modes
- LLM-specific evaluation
- The production concerns specific to agents (checkpointing, governance)

## Why this transition works

LangGraph is a workflow orchestrator. You already know workflow orchestrators (Airflow, Dagster, Prefect). The mental model transfers: nodes are tasks, edges are dependencies, state is the data flowing through. The new part is that some "tasks" are LLM calls, which are probabilistic and slow. Your pipeline instincts (idempotency, retries, observability) are exactly what agent production needs.

## Suggested path

1. [01 Foundations](../01-foundations/) - 2 weeks. The LLM fundamentals are new; the prompt engineering is new.
2. [02 LangGraph core](../02-langgraph-core/) - 2 weeks. This maps to your orchestrator experience; move quickly but pay attention to checkpointing and HITL.
3. [03 Agents in practice](../03-agents-in-practice/) - 2 weeks. Persistence maps to your database experience.
4. [04 Tools and MCP](../04-tools-and-mcp/) - 2 weeks. MCP is a protocol for tool integration.
5. [05 Agentic patterns](../05-agentic-patterns/) - 3 weeks. The patterns are the heart.
6. [06 Evals and observability](../06-evals-and-observability/) - 2 weeks.
7. [07 Multi-agent and A2A](../07-multi-agent-and-a2a/) - 2 weeks.
8. [08 Production](../08-production/) - 2 weeks. You know most of this; focus on the agent-specific parts.

## Timeline

14-16 weeks at 2-3 hours per day.

## Your advantage

You know pipelines, persistence, and orchestration. These are the backbone of production agents. An agent without durable state, without observability, without proper retry logic is a toy - and you will not build toys.

## Common mistakes for this transition

- Treating LLMs like deterministic transforms. Why: your transforms are deterministic. Fix: LLMs are probabilistic; design for retries, validation, and graceful degradation.
- Skipping the eval chapter. Why: "I will let the data scientists handle it." Fix: in agentic AI, evaluation is for everyone.
- Not learning prompt engineering. Why: it feels like configuration. Fix: prompts are code; learn to write them, version them, test them.

## Projects to build first

- [Project 03: Knowledge manager](../projects/03-knowledge-manager/) - this is a data-heavy project that plays to your strengths (ingestion, indexing, retrieval).
- [Project 07: Real-time anomaly monitor](../projects/07-anomaly-monitor/) - this is a streaming-data project that maps to your pipeline experience.

## Next steps

After you finish the path:

- Read [the field guide](../field-guide/) for career guidance specific to data engineers transitioning to agentic AI.
- Build a portfolio project that involves data ingestion and agent orchestration. The combination is your differentiator.
- Apply for "AI Engineer" or "AI Infrastructure Engineer" roles. Your pipeline skills are a differentiator.
