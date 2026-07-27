# Protocol and trajectory evals

Module: 06-evals-and-observability
Chapter: 04-protocol-evals
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Distinguish outcome evals (was the answer right?) from trajectory evals (was the path right?)
- Implement a tool-call correctness evaluator (right tool, right arguments, right order)
- Implement a path evaluator (did the agent take an efficient path, with no unnecessary tool calls?)
- Use LangSmith's trajectory eval tools

## Prerequisites

- [03 LLM-as-judge](03-llm-as-judge.md)

## Conceptual foundation

Outcome evals measure whether the final answer is correct. Trajectory evals measure whether the agent took the right path to get there. Both matter. An agent that produces the right answer by calling the wrong tools, getting wrong results, and stumbling onto the answer by luck is not a good agent - it is a lucky agent, and luck does not scale.

The three levels of trajectory eval:

1. Tool-call correctness. For each tool call the agent made, was it the right tool, with the right arguments, in the right order? This is the most fine-grained trajectory eval. The dataset must label the expected tool sequence for each input.

2. Path efficiency. Did the agent take the shortest path, or did it call unnecessary tools? An agent that calls 5 tools when 2 would suffice is more expensive and more failure-prone. The eval counts the number of tool calls and compares to the expected minimum.

3. Path validity. Did the agent take a path that could have produced the right answer, even if the final answer was wrong? This is useful for debugging: a wrong answer with a valid path is a synthesis error; a wrong answer with an invalid path is a planning error.

Trajectory evals are harder to write than outcome evals because the dataset must label the expected trajectory, not just the expected output. But they catch failures that outcome evals miss:

- The agent calls `web_search` when it should have called `calculator`. Outcome might be right (the agent eventually figures it out), but the trajectory is wrong.
- The agent calls `web_search` 5 times when 1 would suffice. Outcome is right, but the path is inefficient.
- The agent calls `issue_refund` with the wrong order ID, gets an error, retries with the right ID. Outcome is right, but the trajectory shows a recoverable error that should be fixed.

## Worked example

A trajectory evaluator that checks tool-call correctness. Full code in [`examples/trajectory_eval_demo.py`](../examples/trajectory_eval_demo.py).

```python
from typing import Callable

def trajectory_eval(agent: Callable, input_text: str, expected_tools: list[str]) -> dict:
    result = agent(input_text)
    actual_tools = [call["name"] for call in result.get("tool_calls", [])]

    # Check 1: right tools in the right order
    correct_order = actual_tools == expected_tools

    # Check 2: all expected tools were called (order-independent)
    expected_set = set(expected_tools)
    actual_set = set(actual_tools)
    all_called = expected_set.issubset(actual_set)

    # Check 3: no unnecessary tools
    unnecessary = actual_set - expected_set

    # Check 4: path efficiency (number of calls vs minimum)
    efficiency = len(expected_tools) / max(len(actual_tools), 1)

    return {
        "correct_order": correct_order,
        "all_called": all_called,
        "unnecessary_tools": list(unnecessary),
        "efficiency": efficiency,
        "actual_tools": actual_tools,
        "expected_tools": expected_tools,
    }

# Usage
result = trajectory_eval(
    agent,
    "What's 2+2?",
    expected_tools=["calculator"],  # should only call calculator
)
print(result)
```

## Evaluation

The meta-eval: hand-label 20 trajectories and compare the evaluator's verdict to the human's. The evaluator should agree with the human on at least 90 percent of trajectories.

## Production notes

In production, trajectory evals are most valuable for debugging. When an agent fails, the trajectory eval tells you where it went wrong - which tool call was the wrong one, which argument was bad, where the path diverged from the expected. This is dramatically faster than reading a raw trace. The trajectory eval is also the basis for the "minimum number of tool calls" metric, which is a key cost-control signal.

## Common pitfalls

- Only doing outcome evals. Why: they are easier. Fix: add trajectory evals; they catch different failures.
- Requiring exact order when order does not matter. Why: it feels stricter. Fix: only require exact order when the order is semantically important.
- Not labeling the expected trajectory in the dataset. Why: it is more work. Fix: label it; without it, trajectory evals are impossible.

## Further reading

- [LangSmith trajectory evals](https://docs.smith.langchain.com/evaluation/concepts#trajectory)
- [Agent-as-a-Judge paper](https://arxiv.org/abs/2410.10934)

## Checklist

- [ ] Implement a tool-call correctness evaluator
- [ ] Implement a path-efficiency metric (tool calls vs minimum)
- [ ] Label expected trajectories in the golden dataset
- [ ] Use trajectory evals to debug a specific agent failure
