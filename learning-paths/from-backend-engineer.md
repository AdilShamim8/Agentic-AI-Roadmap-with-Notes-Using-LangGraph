# From backend engineer to agentic AI engineer

A smooth transition. You already know how to build production systems; the new skill is adding LLM orchestration. Expect 3-4 months to job-readiness.

## What you already have

- Production systems - API design, databases, caching, queues, observability
- Python (or another backend language), web frameworks (FastAPI, Django, Flask)
- Docker, Kubernetes, CI/CD
- Cloud platforms (AWS, Azure, GCP)
- Software engineering best practices - testing, code review, version control
- Distributed systems thinking - latency, consistency, failure modes

## What you need to learn

- LLM fundamentals - tokenization, context windows, model selection, cost
- Prompt engineering and prompt versioning
- LangGraph (or another orchestration framework) - state, graphs, checkpointing
- Tool design and MCP - the standard for tool interop
- Agent patterns - ReAct, plan-and-execute, supervisor
- LLM-specific evaluation - LLM-as-judge, golden datasets, trajectory evals
- The production concerns specific to agents - checkpointing, governance, cost optimization

## Why this transition works

Backend engineers are the second-easiest transition (after ML engineers) because agentic AI is fundamentally a backend problem. The agent is a service; it has state, it calls external APIs, it needs persistence, it needs observability, it needs CI/CD. You already know all of that. The new part is the orchestration layer (LangGraph) and the evaluation discipline (which backend engineers often skip but cannot in agentic AI).

## Suggested path

1. [01 Foundations](../01-foundations/) - 2 weeks. The LLM fundamentals (chapter 3) and prompt engineering (chapter 4) are the new material.
2. [02 LangGraph core](../02-langgraph-core/) - 3 weeks. The orchestration framework. Do every chapter.
3. [03 Agents in practice](../03-agents-in-practice/) - 2 weeks. Persistence maps to your database experience; HITL and streaming may be new.
4. [04 Tools and MCP](../04-tools-and-mcp/) - 2 weeks. MCP is a protocol; you know protocols.
5. [05 Agentic patterns](../05-agentic-patterns/) - 3 weeks. The patterns are the heart.
6. [06 Evals and observability](../06-evals-and-observability/) - 2 weeks. This may be new - backend engineers often skip evaluation. Do not skip it here.
7. [07 Multi-agent and A2A](../07-multi-agent-and-a2a/) - 2 weeks.
8. [08 Production](../08-production/) - 2 weeks. You know most of this; focus on the agent-specific parts.

## Timeline

14-16 weeks at 2-3 hours per day.

## Your advantage

You know how to ship production systems. Junior agentic AI engineers often ship agents without proper error handling, observability, or deployment infrastructure - and the agents fail in production. You will not make that mistake. Your production instincts are the differentiator.

## Common mistakes for this transition

- Skipping the eval chapter. Why: "evaluation is for ML engineers." Fix: in agentic AI, evaluation is for everyone. An agent without an eval is a demo.
- Treating the LLM as a deterministic API. Why: APIs are deterministic. Fix: the LLM is probabilistic; design for retries, validation, and graceful degradation.
- Not learning prompt engineering deeply. Why: it feels like configuration. Fix: prompts are code; learn to write them, version them, test them.

## Projects to build first

- [Project 02: Customer support multi-agent](../projects/02-customer-support-multi-agent/) - this is a backend-heavy project that plays to your strengths.
- [Project 09: Agent-as-a-service platform](../projects/09-agent-as-a-service-platform/) - this is a full-stack backend project.

## Next steps

After you finish the path:

- Read [the field guide](../field-guide/) for career guidance specific to backend engineers transitioning to agentic AI.
- Build a portfolio project that ships an agent to production. The deployment is where your backend skills shine.
- Apply for "AI Engineer" roles. Emphasize your production experience; it is rare and valuable.
