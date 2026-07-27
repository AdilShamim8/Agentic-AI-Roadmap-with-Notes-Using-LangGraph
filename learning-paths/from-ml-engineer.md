# From ML engineer to agentic AI engineer

This is probably the easiest transition. The roles are very similar. You replace a call to a locally hosted model with a call to an LLM API. The rest is the same - production serving, monitoring, CI/CD, evaluation. Your engineering instincts transfer directly.

## What you already have

- Production ML systems - deployment, serving, monitoring
- Python, PyTorch or TensorFlow
- Docker, Kubernetes, CI/CD
- Model evaluation and metrics
- Cloud platforms (AWS, Azure, GCP)
- MLOps practices - MLflow, experiment tracking
- Fine-tuning experience
- A deep understanding of model behavior (when a model fails, you can reason about why)

## What you need to learn

- LLM APIs - OpenAI, Anthropic. You are used to hosting models yourself; here you call them as APIs.
- Prompt engineering and prompt versioning. This replaces hyperparameter tuning as the primary lever.
- RAG patterns - vector databases, retrieval strategies, chunking. You know embeddings; the new part is retrieval orchestration.
- Agent patterns - LLMs with tools, orchestration loops, multi-agent. This is the biggest conceptual shift.
- LLM-specific evaluation - different from traditional ML metrics. Hallucination detection, answer quality, tool usage correctness.
- LangGraph and the surrounding ecosystem (MCP, A2A, LangSmith).

## Why this transition works

The task of an ML engineer is to integrate machine learning into a product. The task of an agentic AI engineer is to integrate AI into a product. The difference: agentic AI engineers use third-party models via APIs, while ML engineers own the model weights.

Everything you know about model serving, monitoring, CI/CD, and production reliability applies directly. Your production instincts are the differentiator - junior agentic AI engineers often ship without evals or observability, and you will not make that mistake.

## Suggested path

1. [01 Foundations](../01-foundations/) - 1 week. Skim chapters 1 and 2 (you know this); focus on 3 (LLM fundamentals), 4 (prompt engineering), and 5 (structured outputs).
2. [02 LangGraph core](../02-langgraph-core/) - 2 weeks. This is the core new skill. Do every chapter.
3. [03 Agents in practice](../03-agents-in-practice/) - 2 weeks. Persistence, HITL, streaming.
4. [04 Tools and MCP](../04-tools-and-mcp/) - 2 weeks. MCP is the new standard; learn it well.
5. [05 Agentic patterns](../05-agentic-patterns/) - 3 weeks. The patterns are the heart of agentic AI.
6. [06 Evals and observability](../06-evals-and-observability/) - 2 weeks. This is your superpower - you know evaluation. Adapt it to LLMs.
7. [07 Multi-agent and A2A](../07-multi-agent-and-a2a/) - 2 weeks.
8. [08 Production](../08-production/) - 2 weeks. You know most of this; focus on the agent-specific parts (checkpointing, governance).

Skip [09 Emerging topics](../09-emerging-topics/) for now; come back to it after you have shipped a production agent.

## Timeline

12-15 weeks at 2-3 hours per day. You already have the engineering foundation and production mindset. The work is learning the LLM-specific patterns.

## Your advantage

You understand model behavior deeply. When an LLM is not performing well, you can reason about why - is it a prompt issue, a context issue, or a model limitation? You also know how to serve models locally when API-based solutions are not suitable (privacy, latency, cost). This is valuable for the subset of roles that need self-hosted LLMs.

## Common mistakes for this transition

- Treating prompts like hyperparameters. Why: it feels familiar. Fix: prompts are code, not configuration. Version them, review them, test them.
- Skipping the eval chapter because "you know evaluation." Why: LLM evals are different. Fix: do the chapter; the LLM-as-judge pattern is not the same as accuracy/F1.
- Over-engineering the first agent. Why: you are used to complex ML pipelines. Fix: start with ReAct; upgrade to plan-and-execute only when you hit its limits.

## Projects to build first

- [Project 04: Self-healing code agent](../projects/04-self-healing-code-agent/) - this plays to your strengths (you know testing and code review).
- [Project 10: Eval harness and benchmark](../projects/10-eval-harness-and-benchmark/) - evaluation is your superpower; this project demonstrates it.

## Next steps

After you finish the path:

- Read [the field guide](../field-guide/) for career guidance specific to ML engineers transitioning to agentic AI.
- Start a portfolio project that uses an LLM in production. The portfolio matters more than the resume.
- Apply for roles with "AI Engineer" or "Applied AI Engineer" in the title. Your ML background is a strength, not a weakness.
