# The agentic AI engineer role

Based on analysis of job postings on builtin.com (January-July 2026) and practitioner reports.

This is my vision of the role. To see how it compares with what companies look for, see [02 Skills that matter](02-skills-that-matter.md).

## Core responsibility

- Integrating agentic AI into a product - the LLM, the tools, the orchestration, the evaluation, the deployment.
- Working with LLM providers (OpenAI, Anthropic, Google) through their APIs.
- Working with product managers to identify problems where agents (not just LLM calls) are the right solution.
- Not "AI is cool, let's use it" - starts from a real problem and decides whether an agent is the right abstraction.

## Beyond "just call the API"

Even for a simple use case like a customer-support agent, professional agentic AI engineering requires:

1. Tool design - schemas, descriptions, error returns (covered in [04 Tools and MCP](../04-tools-and-mcp/)).
2. Evaluation dataset - golden inputs to verify quality, gives a metric (covered in [06 Evals and observability](../06-evals-and-observability/)).
3. Iterating on the prompt - change prompt, run eval, verify no degradation.
4. Rolling out to users - A/B test with a small portion first.
5. Production monitoring - dashboard for error rates, failure cases, cost, latency.
6. Collecting logs - inspect inputs, outputs, find misalignments.
7. Human annotators - sample production data, verify quality, add problematic cases to eval set.
8. Model updates - new model from provider? Run eval set to check for regressions.
9. Prompt versioning - version control for prompts, experiment tracking (covered in [01 Foundations](../01-foundations/04-prompt-engineering.md)).
10. Feedback from users - explicit (thumbs up/down) and implicit (user corrects output, user re-asks).

## Progressive complexity

- Simple case: user input -> prompt + LLM API -> response. This is not an agent; it is a chain.
- RAG (~5x harder): add data pipelines, search engine (vector/text), retrieval, infrastructure, reliability.
- Single agent (~10x harder): add tool calls, multiple LLM rounds, multi-step evaluation, trace instrumentation, tool rollout management.
- Multi-agent (~20x harder): add inter-agent coordination, handoffs, shared state, multi-agent evals, multi-agent cost control.

Most "agentic AI engineer" roles are at the single-agent level. Senior roles involve multi-agent. Staff roles involve designing the multi-agent architecture for an organization.

## How it compares to other roles

### vs ML engineer

- Very similar roles. The easiest transition into agentic AI is from ML engineering.
- ML engineers own model weights; agentic AI engineers use third-party models via APIs.
- Replace a call to a locally hosted model with a call to OpenAI - the rest is the same.
- ML engineers need to add: agent patterns, LLM-specific evaluation, prompt engineering.
- Agentic AI engineers need to add: nothing (the ML skills transfer, but are not required).

### vs Data scientist

- Data scientists focus on model creation: translating requirements to ML, designing datasets, training.
- Agentic AI engineers do both science and engineering, but no real modeling - the model already exists.
- Most effort goes to prompt and agent design instead of model training.
- Data scientists need to add: engineering skills (tests, CI/CD, deployment), agent patterns.

### vs Backend engineer

- Backend engineers focus on the system around the model; agentic AI engineers focus on the model and the system.
- The production concerns (deployment, observability, scaling) are the same.
- Backend engineers need to add: LLM fundamentals, prompt engineering, agent patterns, evaluation.

### What agentic AI engineers do not do

- Train models from scratch (that is ML engineering).
- Build custom model architectures (that is ML research).
- Heavy feature engineering (that is traditional data science).
- Build the data pipeline (that is data engineering).

### What agentic AI engineers focus on

- Agent architecture: which pattern (ReAct, supervisor, plan-and-execute) for which problem.
- Tool design: schemas, descriptions, error handling.
- Prompt engineering and versioning.
- Evaluation: golden datasets, LLM-as-judge, trajectory evals.
- Production: deployment, observability, cost optimization, governance.

## In bigger organizations

- Agentic AI responsibilities often split between existing AI engineers, ML engineers, and backend engineers.
- AI engineers: prompt tuning, agent design, validation framework.
- ML engineers: model selection, fine-tuning (when needed), evaluation methodology.
- Backend engineers: deployment, observability, infrastructure.
- Eventually a dedicated agentic AI engineer might be hired to own the full stack.
- LLMs are not the answer to all problems - traditional ML work continues alongside agentic AI.

## What is different in 2026

The role has matured since 2023. Three things are different:

1. The reference stack has converged. In 2023, every team used a different framework. In 2026, the stack is LangGraph (orchestration) + MCP (tools) + A2A (agents) + LangSmith (eval and observability). Knowing this stack is table stakes.

2. Evaluation is now non-negotiable. In 2023, you could ship an agent without an eval. In 2026, the eval suite is the deliverable - the agent is just the code that passes the eval. Engineers who cannot build eval suites are not hired.

3. Multi-agent is mainstream. In 2023, multi-agent was research. In 2026, every enterprise AI team has at least one multi-agent system in production. Engineers who can design multi-agent architectures are in high demand.
