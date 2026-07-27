# Why evals

Module: 06-evals-and-observability
Chapter: 01-why-evals
Status: stable
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Make the argument for evals in language a stakeholder will accept
- Quantify the cost of not evaluating (production incidents, model-update regressions, unmeasurable quality)
- Distinguish agent evals from traditional ML evals (no single ground truth, trajectory matters, cost is a signal)
- Set up the minimum viable eval: a golden dataset, an evaluator, a CI gate

## Prerequisites

- [05 Agentic patterns](../05-agentic-patterns/)

## Conceptual foundation

An agent without an eval is a demo. An agent with an eval is a system. The eval is what allows you to ship with confidence, upgrade models without fear, and demonstrate quality to stakeholders. Without an eval, you are relying on "it looks fine to me" - which is not a quality strategy.

The argument for evals, in three points:

1. Model updates break agents silently. LLM providers ship updates regularly. Each update shifts behavior slightly - a tool-call argument that was 98 percent accurate drops to 92 percent, and your agent starts failing in ways that are hard to reproduce. Without an eval, you find out from user complaints. With an eval, you find out before you ship.

2. "It works" is not measurable. Stakeholders ask "how good is the agent?" Without an eval, the answer is "seems fine." With an eval, the answer is "92 percent tool-selection accuracy, 88 percent answer correctness, $0.03 average cost per request, 4.2 second p95 latency." Measurable quality is the difference between an AI feature and an AI product.

3. Iteration requires a feedback loop. You change a prompt. Is the agent better or worse? Without an eval, you guess. With an eval, you know. The eval is what makes prompt engineering a discipline rather than a superstition.

Agent evals differ from traditional ML evals in three ways:

1. No single ground truth. A traditional classifier has one right answer; an agent might have many valid trajectories. The eval must accept multiple correct paths.

2. Trajectory matters. Two agents that produce the same final answer might have taken very different paths - one called the right tools in the right order, the other called the wrong tools, got wrong results, and stumbled onto the right answer by luck. The trajectory eval catches the second case.

3. Cost and latency are quality signals. A traditional model has a fixed cost per inference. An agent's cost varies wildly based on how many tools it calls and how long the conversation gets. An agent that produces correct answers but costs $1 per request is not a good agent; the eval must include cost.

The minimum viable eval has three parts:

1. A golden dataset of 20-50 inputs, hand-labeled with expected outputs (or expected trajectories).

2. An evaluator that scores the agent's output against the expected output. Can be rule-based (exact match, regex match) or LLM-as-judge.

3. A CI gate that runs the eval on every PR and blocks merges on regressions.

You will build all three in the following chapters.

## Worked example

No code in this chapter. The first code is in the next chapter. But here is what the minimum viable eval looks like in practice, for a customer-support agent:

- Golden dataset: 30 customer messages, each labeled with the expected intent (refund, bug, feature_request) and the expected tool call (issue_refund, escalate_to_human, search_docs).
- Evaluator: rule-based check that the routed intent matches the label, and that the agent called the expected tool.
- CI gate: a GitHub Actions workflow that runs the eval on every PR, posts the diff as a PR comment, and blocks merge if tool-selection accuracy drops below 90 percent.

This is the minimum. It catches regressions. It does not catch everything (it does not measure answer quality, only tool selection). But it is the difference between shipping blind and shipping with a safety net.

## Evaluation

There is no eval for this chapter - it is the argument for evals. The checklist below is the self-test.

## Production notes

In production, the eval suite grows over time. Start with 20 rows and three evaluators. Add rows from production failures (every user complaint becomes a new row). Add evaluators as new failure modes appear. A mature eval suite has 200+ rows and 5-10 evaluators, and runs in under 10 minutes in CI.

The most common production failure: the eval suite is too slow, so developers skip it. The fix: parallelize the eval (run rows concurrently), cache LLM-as-judge results, and keep the suite under 10 minutes. If it grows past that, split it into a fast suite (runs on every PR) and a slow suite (runs nightly).

## Common pitfalls

- No eval at all. Why: "the agent works fine." Fix: build the minimum viable eval before shipping.
- Eval that only checks the final answer. Why: it is the easiest to write. Fix: add trajectory evals (chapter 4).
- Eval that is too slow to run in CI. Why: the dataset grew without optimization. Fix: parallelize, cache, split into fast and slow suites.
- Eval that nobody looks at. Why: it runs but does not block. Fix: make it a CI gate.

## Further reading

- [Hamel Husain: Evaluating LLM Applications](https://hamel.dev/blog/posts/evals/)
- [Eugene Yan: Evaluating LLM Applications](https://eugeneyan.com/writing/evaluating-llm-applications/)
- [LangSmith evaluation docs](https://docs.smith.langchain.com/evaluation)

## Checklist

- [ ] Make the argument for evals in three sentences a stakeholder would accept
- [ ] Distinguish agent evals from traditional ML evals (no single ground truth, trajectory matters, cost is a signal)
- [ ] Name the three parts of the minimum viable eval
- [ ] Plan the first 20 rows of a golden dataset for an agent you are building
