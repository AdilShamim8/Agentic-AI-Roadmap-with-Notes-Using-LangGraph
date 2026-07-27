# Eval rubric - [Agent name]

## What this eval measures

[One paragraph. The capability being evaluated. The failure modes it catches.]

## Dataset

- Source: [where the data came from]
- Size: [N rows]
- Schema: [columns and types]
- License: [license]
- Versioning: [how the dataset is versioned]

## Evaluators

| Evaluator | Type | What it checks | Pass threshold |
|-----------|------|----------------|----------------|
| [Name] | rule-based | [what] | [threshold] |
| [Name] | LLM-as-judge | [what] | [threshold] |
| [Name] | trajectory | [what] | [threshold] |

## Judge prompt

[The exact prompt used for the LLM-as-judge evaluator. This must be versioned with the dataset. Any change to the judge prompt is a new eval version.]

## Running the eval

```bash
make eval agent=[path] dataset=[name]
```

## Interpreting results

[How to read the report. What a regression looks like. What to do when the eval passes but the agent is still bad in production. What to do when the eval fails but the agent is actually correct.]

## Inter-rater reliability

[For LLM-as-judge evaluators. Sample 100 rows, hand-label them, compute Cohen's kappa between the judge and the human. If kappa is below 0.6, the judge prompt needs revision. Report the last measured kappa here.]
