# LLM-as-judge

Module: 06-evals-and-observability
Chapter: 03-llm-as-judge
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement an LLM-as-judge evaluator with a versioned rubric
- Diagnose and mitigate judge bias (position bias, length bias, self-preference)
- Measure inter-rater reliability (Cohen's kappa) between the judge and a human
- Choose between rule-based, LLM-as-judge, and human evaluators based on the eval need

## Prerequisites

- [02 Golden datasets](02-golden-datasets.md)

## Conceptual foundation

LLM-as-judge is the pattern of using an LLM to evaluate the output of another LLM. It is the only practical way to evaluate open-ended outputs (answer quality, writing quality, tone) at scale. Rule-based evaluators cannot judge whether an answer is "helpful"; LLM-as-judge can.

The components:

1. Rubric. A description of what a good output looks like, broken into dimensions. For a customer-support answer, the rubric might have dimensions: correctness (does the answer address the question?), tone (is it polite and professional?), completeness (does it provide all needed information?), safety (does it avoid harmful advice?).

2. Judge prompt. The prompt sent to the judge LLM. It includes the rubric, the input, the output to evaluate, and an instruction to produce a structured score. The judge prompt is versioned with the rubric.

3. Judge LLM. The model used as the judge. Use a stronger model than the one being evaluated (e.g., evaluate GPT-4o outputs with Claude Opus, or vice versa). Using the same model as both actor and judge produces self-preference bias.

4. Score aggregation. For multi-dimensional rubrics, aggregate the per-dimension scores into a single score (weighted average, minimum, etc.).

The biases to mitigate:

1. Position bias. If the judge sees two outputs and is asked which is better, it prefers the first one. Fix: randomize the order, or evaluate each output independently.

2. Length bias. The judge prefers longer outputs, even when they are not better. Fix: include "be concise" in the rubric, or normalize scores by length.

3. Self-preference. The judge prefers outputs from its own model family. Fix: use a different model family for the judge than for the actor.

4. Drift. The judge's behavior shifts as the underlying model is updated. Fix: pin the judge model version, re-run the inter-rater reliability check periodically.

Inter-rater reliability is the meta-eval: how well does the judge agree with a human? Sample 100 rows, have a human label them, compute Cohen's kappa. Kappa above 0.6 is acceptable; above 0.8 is good. If kappa is below 0.6, the rubric is ambiguous or the judge is not capable; revise the rubric or use a stronger judge model.

## Worked example

An LLM-as-judge evaluator for answer quality. Full code in [`examples/llm_judge_demo.py`](../examples/llm_judge_demo.py).

```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class AnswerScore(BaseModel):
    correctness: int = Field(description="Score 1-5: does the answer address the question correctly?")
    completeness: int = Field(description="Score 1-5: does it provide all needed information?")
    tone: int = Field(description="Score 1-5: is it polite and professional?")
    explanation: str = Field(description="One sentence explaining the scores.")

JUDGE_PROMPT = """You are evaluating a customer support answer.

Question: {question}
Answer: {answer}

Score each dimension 1-5:
- correctness: does the answer address the question correctly?
- completeness: does it provide all needed information?
- tone: is it polite and professional?

Be strict. A score of 5 means excellent; 3 means acceptable; 1 means poor.
"""

def judge_answer(question: str, answer: str) -> AnswerScore:
    llm = ChatOpenAI(model="claude-3-5-sonnet", temperature=0)  # different model from actor
    prompt = JUDGE_PROMPT.format(question=question, answer=answer)
    return llm.with_structured_output(AnswerScore).invoke(prompt)

# Usage
score = judge_answer("How do I reset my password?", "Click 'Forgot Password' on the login page.")
print(score.correctness, score.completeness, score.tone)
```

## Evaluation

The meta-eval: sample 100 rows, have a human label them with the same rubric, compute Cohen's kappa between the judge and the human on each dimension. Document the kappa in the eval rubric file.

## Production notes

In production, LLM-as-judge has a cost: each row in the eval costs a judge LLM call. For a 200-row dataset, that is 200 LLM calls per eval run. In CI (running on every PR), this adds up. The mitigations: cache judge results for unchanged rows (the input and output are the same, so the judge result is the same), use a cheaper judge model for CI and a stronger one for nightly runs, and split the dataset into a CI subset (50 rows) and a full subset (200 rows).

## Common pitfalls

- Using the same model as actor and judge. Why: it is convenient. Fix: use a different model family for the judge.
- No rubric, just "is this good?" Why: it feels simpler. Fix: write a multi-dimensional rubric; without it, the judge is inconsistent.
- No inter-rater reliability check. Why: the judge "looks right." Fix: measure kappa; if it is below 0.6, the eval is not trustworthy.
- Not versioning the judge prompt. Why: it changes rarely. Fix: version it; a judge prompt change is a new eval version.

## Further reading

- [LangSmith LLM-as-judge](https://docs.smith.langchain.com/evaluation/concepts#llm-as-judge)
- [Agent-as-a-Judge paper](https://arxiv.org/abs/2410.10934)
- [Hamel Husain: LLM-as-judge pitfalls](https://hamel.dev/blog/posts/evals/)

## Checklist

- [ ] Implement an LLM-as-judge evaluator with a multi-dimensional rubric
- [ ] Use a different model family for the judge than for the actor
- [ ] Measure Cohen's kappa between the judge and a human on 100 rows
- [ ] Version the judge prompt and the rubric
