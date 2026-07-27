# From data scientist to agentic AI engineer

Evaluation is your superpower. The transition is about adding engineering rigor to your evaluation skills and learning the agent-specific patterns.

## What you already have

- Statistics and experimental design (which maps directly to A/B testing agents)
- Python, pandas, scikit-learn
- Model evaluation - you know how to measure things
- Data wrangling - cleaning, labeling, analyzing
- Business sense - you know why we build models (to make decisions)
- Visualization and communication

## What you need to learn

- Software engineering practices - tests, CI/CD, version control beyond notebooks
- LLM APIs and prompt engineering
- LangGraph or another orchestration framework
- Production deployment - Docker, cloud platforms
- Agent-specific patterns and their failure modes
- The LLM-specific eval patterns that build on what you already know

## Why this transition works

Data scientists are the hardest transition among the engineering roles, because the gap is engineering rigor, not analytical skill. But the analytical skill is the hard part to teach, and you already have it. Once you add engineering practices (tests, CI/CD, deployment), you become an agentic AI engineer who can measure things - which is exactly what the field needs.

## Suggested path

1. [01 Foundations](../01-foundations/) - 2 weeks. The LLM fundamentals and prompt engineering are new.
2. [02 LangGraph core](../02-langgraph-core/) - 3 weeks. This is the orchestration layer.
3. [03 Agents in practice](../03-agents-in-practice/) - 2 weeks.
4. [04 Tools and MCP](../04-tools-and-mcp/) - 2 weeks.
5. [05 Agentic patterns](../05-agentic-patterns/) - 3 weeks.
6. [06 Evals and observability](../06-evals-and-observability/) - 1 week. This is your wheelhouse; move quickly through it but pay attention to the LLM-specific patterns (LLM-as-judge, trajectory evals).
7. [07 Multi-agent and A2A](../07-multi-agent-and-a2a/) - 2 weeks.
8. [08 Production](../08-production/) - 3 weeks. This is the gap. Spend extra time here; learn Docker, CI/CD, deployment.

## Timeline

16-18 weeks at 2-3 hours per day. The extra time is for the engineering practices you may not have.

## Your advantage

You can measure things. Most agentic AI engineers cannot - they ship agents without evals and hope for the best. Your ability to design experiments, build datasets, and run rigorous evaluations is the single most valuable skill in agentic AI in 2026.

## Common mistakes for this transition

- Skipping the production chapters. Why: "I will let the engineers handle deployment." Fix: learn to deploy; an agent you cannot deploy is not finished.
- Staying in notebooks. Why: notebooks are comfortable. Fix: move to .py files with tests; notebooks are for exploration, not production.
- Not learning software engineering practices. Why: "I am analytical, not an engineer." Fix: tests, CI/CD, and version control are non-negotiable for production agents.

## Projects to build first

- [Project 10: Eval harness and benchmark](../projects/10-eval-harness-and-benchmark/) - this is your superpower; demonstrate it.
- [Project 03: Knowledge manager](../projects/03-knowledge-manager/) - this combines RAG (which you may know) with agent patterns.

## Next steps

After you finish the path:

- Read [the field guide](../field-guide/) for career guidance specific to data scientists transitioning to agentic AI.
- Build a portfolio project that includes a rigorous eval suite. The eval is what will set you apart.
- Apply for "AI Engineer" or "Applied AI Engineer" roles. Your evaluation skills are a differentiator.
