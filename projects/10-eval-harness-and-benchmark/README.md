# Project 10 - Eval harness and benchmark

Difficulty: ⭐⭐⭐⭐
Estimated time: 3-4 weeks
Status: spec

## Problem

A reusable eval harness that can evaluate any LangGraph agent against a standardized benchmark, with per-pattern golden datasets and LLM-as-judge evaluators. The harness is the "pytest for agents" - a tool that any agentic AI engineer can drop into their project to get a real eval suite.

This project exercises the evaluation discipline from module 06 at its fullest. It is the canonical "eval" project, and it is the project that most directly demonstrates the skill that separates senior agentic AI engineers from junior ones.

## Architecture

1. Harness CLI (Python, Rich for terminal UI): `eval run --agent <path> --dataset <name>`.
2. Benchmark registry: YAML files declaring datasets and evaluators per pattern (ReAct, plan-and-execute, supervisor, etc.).
3. Runner: executes the agent against each row in the dataset.
4. Evaluators: rule-based, LLM-as-judge, trajectory. Each evaluator is a Python class with a standard interface.
5. Reporter: Markdown report with per-test pass/fail, per-evaluator scores, and a comparison to baseline.

## Stack

- Orchestration: none (this is a tool, not an agent)
- LLM: GPT-4o or Claude (for LLM-as-judge evaluators)
- Frameworks: pytest (for the runner), Pydantic (for schemas), Rich (for the CLI)
- LangSmith: optional, for trace-level analysis

## Eval rubric (meta - the harness evaluates itself)

| Metric | Target | How measured |
|--------|--------|--------------|
| Pattern coverage | 5+ patterns | ReAct, plan-and-execute, supervisor, swarm, map-reduce |
| Evaluator reliability | kappa > 0.6 | Inter-rater agreement on 100 samples |
| Runtime | under 10 minutes | For a 50-row dataset against one agent |
| Reproducibility | within 2 percentage points | Same agent, same dataset, same evaluator |

## Datasets

- 5 golden datasets, one per pattern (50 rows each)
- Hand-labeled trajectories for trajectory evaluators
- Adversarial cases for each pattern

## Stretch goals

- Support non-LangGraph agents (OpenAI Agents SDK, CrewAI) via A2A
- Support online evals (evaluate production traffic)
- Support comparative evals (A/B test two agent versions)

## References

- [LangSmith evaluation](https://docs.smith.langchain.com/evaluation)
- [pytest](https://docs.pytest.org/) - the runner inspiration
- [Hamel Husain's evals work](https://hamel.dev/blog/posts/evals/)
- Real job postings: search "AI engineer" + "evaluation" on builtin.com

## Solution

Reference solution: [projects/-solutions/10-eval-harness-and-benchmark/](-solutions/10-eval-harness-and-benchmark/) (coming soon). Build your own first.
