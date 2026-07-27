# Reflexion

Module: 05-agentic-patterns
Chapter: 03-reflexion
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement reflexion: an actor generates, an evaluator critiques, a self-reflector revises
- Distinguish reflexion from simple retry (reflexion produces explicit, reusable reflections)
- Use reflexion with persistent memory (the reflections are stored and reused on future tasks)
- Choose between reflexion and plan-and-execute based on failure mode

## Prerequisites

- [01 ReAct](01-react.md)
- [02 Plan-and-execute](02-plan-and-execute.md)

## Conceptual foundation

Reflexion (Shinn et al., 2023) is a pattern where an agent critiques its own output and revises it. Unlike simple retry (which just tries again), reflexion produces an explicit verbal reflection - "I made this mistake because..." - that is fed back into the next attempt. The reflection is also stored in memory and can be retrieved on future tasks, which means the agent learns from its mistakes over time.

The three components:

1. Actor. Generates output (an answer, a code patch, a plan). Typically a ReAct or plan-and-execute agent.

2. Evaluator. Scores the output. Can be rule-based (does the code pass tests?), LLM-as-judge (is the answer correct and well-cited?), or human.

3. Self-reflector. Looks at the output, the score, and the actor's trajectory. Produces a verbal reflection: what went wrong, what to do differently next time. The reflection is added to the actor's prompt for the next attempt.

The loop: actor generates, evaluator scores, self-reflector reflects, actor regenerates with the reflection. Repeat until the evaluator is satisfied or a max-iteration limit is hit.

The memory component: reflections are stored in a vector store. On a new task, the agent retrieves reflections from similar past tasks and includes them in the initial prompt. This is how reflexion produces learning across tasks, not just within a single task.

Reflexion is more expensive than simple retry (one extra LLM call per iteration for the self-reflector) but more effective (the explicit reflection guides the next attempt rather than hoping the LLM does better on a second try). Use reflexion when the task is hard enough that simple retry does not work - typically, tasks where the actor's failure has a specific, identifiable cause.

## Worked example

A reflexion agent that writes code and learns from test failures. Full code in [`examples/reflexion_demo.py`](../examples/reflexion_demo.py).

```python
from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class State(TypedDict):
    task: str
    code: str
    test_result: str
    passed: bool
    reflections: Annotated[list[str], add]
    iteration: int

def generate(state: State) -> dict:
    prompt = f"Write Python code for: {state['task']}"
    if state.get("reflections"):
        prompt += f"\n\nPast reflections:\n" + "\n".join(f"- {r}" for r in state["reflections"])
    msg = llm.invoke(prompt)
    return {"code": msg.content, "iteration": state["iteration"] + 1}

def run_tests(state: State) -> dict:
    # In production, actually run the code against a test suite
    passed = "def " in state["code"]  # toy check
    return {"passed": passed, "test_result": "passed" if passed else "no function defined"}

def reflect(state: State) -> dict:
    if state["passed"]:
        return {}
    msg = llm.invoke(
        f"The code failed tests:\n\nCode:\n{state['code']}\n\nTest result: {state['test_result']}\n\n"
        f"What went wrong and what should be done differently? Reply with one sentence."
    )
    return {"reflections": [msg.content]}

def route(state: State) -> str:
    if state["passed"] or state["iteration"] >= 3:
        return "__end__"
    return "generate"

g = StateGraph(State)
g.add_node("generate", generate)
g.add_node("test", run_tests)
g.add_node("reflect", reflect)
g.add_edge(START, "generate")
g.add_edge("generate", "test")
g.add_edge("test", "reflect")
g.add_conditional_edges("reflect", route)

agent = g.compile()
```

## Evaluation

A golden dataset of 10 coding tasks with known-correct solutions. The evaluator checks: (1) the final code passes the tests, (2) the agent did not exceed 3 iterations, (3) the reflections are specific and actionable (not "try again").

## Production notes

In production, reflexion's memory component is the differentiator. Without memory, reflexion is just retry with extra LLM calls. With memory, the agent improves over time on similar tasks. The memory is typically a vector store of reflections, retrieved by similarity to the current task. The retrieval is cheap; the win is large for repeated task types (e.g., the same kind of coding task, the same kind of customer support issue).

## Common pitfalls

- Reflexion without memory. Why: it is simpler. Fix: add memory; without it, reflexion is not learning.
- Reflections that are too vague. Why: the LLM produces "I should try harder." Fix: prompt the reflector to produce specific, actionable reflections.
- Not capping iterations. Why: it works in dev. Fix: cap at 3-5.

## Further reading

- [Reflexion paper](https://arxiv.org/abs/2303.11366)
- [LangGraph reflexion example](https://langchain-ai.github.io/langgraph/tutorials/reflexion/reflexion/)

## Checklist

- [ ] Implement reflexion with actor, evaluator, and self-reflector
- [ ] Add a memory component that stores and retrieves reflections
- [ ] Cap iterations at 3-5
- [ ] Prompt the reflector to produce specific, actionable reflections
