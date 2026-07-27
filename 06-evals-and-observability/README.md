# 06 - Evals and observability

The discipline that separates professionals from hobbyists. By the end of this module, every agent you ship has an eval suite that runs in CI, blocks on regressions, and posts diffs to PRs.

## What you will learn

- Why evals are non-negotiable for production agents
- Building golden datasets from production samples and adversarial cases
- LLM-as-judge with versioned rubrics and inter-rater reliability
- Trajectory and protocol evals (did the agent take the right path, not just produce the right answer)
- LangSmith tracing, dashboards, and alerting
- Cost and latency tracking as quality signals
- Running the eval suite as a CI gate

## Chapters

- [01 Why evals](01-why-evals.md) - the argument and the cost of not evaluating
- [02 Golden datasets](02-golden-datasets.md) - sourcing, labeling, versioning, augmenting
- [03 LLM-as-judge](03-llm-as-judge.md) - rubrics, judge bias, inter-rater reliability
- [04 Protocol and trajectory evals](04-protocol-evals.md) - tool-call correctness, path evaluation
- [05 LangSmith tracing](05-langsmith-tracing.md) - instrumentation, dashboards, alerting
- [06 Cost and latency](06-cost-and-latency.md) - tracking, budgeting, model routing
- [07 Regression suites in CI](07-regression-suites-in-ci.md) - the end state

## Prerequisites

- [05 Agentic patterns](../05-agentic-patterns/)

## Time

2 to 3 weeks at 2 to 3 hours per day.

## What is next

After this module, you are ready for [07 Multi-agent and A2A](../07-multi-agent-and-a2a/), where you will scale from single-agent to multi-agent systems.
