# Regression suites in CI

Module: 06-evals-and-observability
Chapter: 07-regression-suites-in-ci
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Wire an eval suite into GitHub Actions so it runs on every PR
- Block merges on regressions (configurable thresholds per metric)
- Post eval diffs as PR comments so reviewers can see the impact
- Maintain a fast CI eval (under 10 minutes) and a slow nightly eval

## Prerequisites

- All chapters in this module

## Conceptual foundation

The eval suite is only valuable if it runs. The most reliable way to make it run is to wire it into CI: every PR triggers the eval, the eval posts its results as a PR comment, and the PR cannot merge if the eval regresses. This is the end state of evaluation - it becomes a gate, not a suggestion.

The components:

1. The eval script. A Python script that loads the agent, loads the golden dataset, runs the agent on each row, scores the outputs, and produces a report (Markdown, with per-metric scores and a comparison to the baseline).

2. The baseline. The eval scores from the last known-good run (typically, the main branch). The PR's eval scores are compared to the baseline. A regression is a score that dropped below a threshold.

3. The CI workflow. A GitHub Actions workflow that runs on PRs, executes the eval script, compares to the baseline, posts the diff as a PR comment, and sets a status check that blocks merge on regression.

4. The fast and slow split. The fast suite (50 rows, rule-based evaluators) runs on every PR and must complete in under 10 minutes. The slow suite (200 rows, LLM-as-judge evaluators) runs nightly and on demand. PRs are gated by the fast suite; the slow suite catches subtle regressions that the fast suite misses.

The thresholds: each metric has a pass threshold (e.g., "tool-selection accuracy must be >= 90 percent") and a regression threshold (e.g., "a drop of more than 2 percentage points from baseline is a regression"). The pass threshold catches absolute quality; the regression threshold catches relative drift. Both are needed.

## Worked example

The CI workflow (already in `.github/workflows/eval-regression.yml`) and the eval script it runs. The eval script produces a Markdown report that the workflow posts as a PR comment. Full code in [`examples/run_evals.py`](../examples/run_evals.py).

```python
# examples/run_evals.py (simplified)
import csv, json, sys
from agent import build_agent  # your agent

def run_eval():
    baseline = json.load(open("eval_baseline.json"))
    rows = list(csv.DictReader(open("datasets/support_eval_30rows.csv")))
    agent = build_agent()

    correct_intent = 0
    correct_tool = 0
    for row in rows:
        result = agent(row["input"])
        if result["intent"] == row["expected_intent"]:
            correct_intent += 1
        if result["tool_called"] == row["expected_tool"]:
            correct_tool += 1

    n = len(rows)
    current = {
        "intent_accuracy": correct_intent / n,
        "tool_accuracy": correct_tool / n,
    }

    # Compare to baseline
    report = ["# Eval Report\n", "| Metric | Baseline | Current | Delta | Status |",
              "|--------|----------|---------|-------|--------|"]
    for k in current:
        delta = current[k] - baseline.get(k, 0)
        status = "PASS" if delta >= -0.02 else "REGRESSION"
        report.append(f"| {k} | {baseline.get(k, 0):.3f} | {current[k]:.3f} | {delta:+.3f} | {status} |")

    with open("eval_report.md", "w") as f:
        f.write("\n".join(report))

    # Exit non-zero on regression (CI gate)
    if any(current[k] - baseline.get(k, 0) < -0.02 for k in current):
        sys.exit(1)

if __name__ == "__main__":
    run_eval()
```

## Evaluation

The meta-eval: the CI eval itself must be reliable. If it produces flaky results (passes one run, fails the next with no code change), developers will lose trust and disable it. The defenses: pin all model versions (no "latest" model), set temperature to 0, cache LLM-as-judge results, and re-run failed evals automatically to filter flakes.

## Production notes

In production, the CI eval is the most important quality gate. Treat it like a test suite: it must be fast (under 10 minutes), reliable (no flakes), and actionable (a failure tells you what broke). The most common production failure: the eval is too slow, so developers bypass it. The fix: split into fast and slow suites, parallelize the fast suite, cache aggressively.

The second most common failure: the eval passes but the agent is bad in production. This happens when the dataset does not represent production traffic. The fix: continuously update the dataset from production samples (chapter 2).

## Common pitfalls

- Not gating merges. Why: the eval runs but does not block. Fix: make it a required status check.
- Flaky eval. Why: model randomness. Fix: pin models, temperature 0, cache, re-run on failure.
- Eval too slow. Why: the dataset grew. Fix: split into fast and slow, parallelize.
- No baseline. Why: "we will compare to last week." Fix: maintain a baseline file; update it on every merge.

## Further reading

- [LangSmith CI/CD](https://docs.smith.langchain.com/evaluation/ci)
- [GitHub Actions: required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/managing-a-branch-protection-rule)

## Checklist

- [ ] Wire an eval suite into GitHub Actions that runs on every PR
- [ ] Post eval diffs as PR comments
- [ ] Make the eval a required status check that blocks merge on regression
- [ ] Split into a fast suite (under 10 minutes, every PR) and a slow suite (nightly)
