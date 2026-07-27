# Plan-and-execute

Module: 05-agentic-patterns
Chapter: 02-plan-and-execute
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement plan-and-execute: a planner produces a step list, executors run each step, a replanner revises the plan based on results
- Choose between ReAct and plan-and-execute based on task structure
- Diagnose plan-and-execute failure modes (bad initial plan, steps that depend on unanticipated results, replanning loops)
- Use plan-and-execute with both StateGraph and the Functional API

## Prerequisites

- [01 ReAct](01-react.md)

## Conceptual foundation

Plan-and-execute addresses ReAct's main weakness: on long tasks, the LLM loses sight of the goal. The pattern splits the agent into two roles:

1. Planner. Takes the user's goal and produces a list of steps. Each step is a self-contained task (e.g., "search for Tokyo population", "calculate population * 2", "format the answer").

2. Executor. Takes one step and executes it, typically as a ReAct agent with tools. Returns the result.

3. Replanner. After each step, looks at the results so far and the remaining steps. Decides: continue with the current plan, revise the plan based on new information, or declare the task complete.

The advantage over ReAct: the plan is an explicit artifact. The LLM can refer back to it after each step, which keeps it on track for long tasks. The replanner can adapt when a step produces unexpected results, which ReAct cannot do well.

The disadvantage: more LLM calls (planner + executor + replanner per step, vs. one LLM call per step in ReAct). Higher cost, higher latency. Use plan-and-execute when the task is complex enough to justify the overhead - typically, tasks with 5 or more steps.

## Worked example

A plan-and-execute agent that answers multi-step research questions. Full code in [`examples/plan_execute_demo.py`](../examples/plan_execute_demo.py).

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

class State(TypedDict):
    goal: str
    plan: list[str]
    results: list[str]
    step_index: int
    done: bool

def planner(state: State) -> dict:
    msg = llm.invoke(
        f"Break this goal into 3-5 steps. Reply with one step per line.\n\nGoal: {state['goal']}"
    )
    steps = [s.strip() for s in msg.content.strip().split("\n") if s.strip()]
    return {"plan": steps, "step_index": 0, "results": []}

def executor(state: State) -> dict:
    step = state["plan"][state["step_index"]]
    msg = llm.invoke(f"Execute this step and return the result:\n\nStep: {step}\n\nPrevious results: {state['results']}")
    return {"results": state["results"] + [msg.content], "step_index": state["step_index"] + 1}

def replanner(state: State) -> dict:
    if state["step_index"] >= len(state["plan"]):
        return {"done": True}
    msg = llm.invoke(
        f"Given these results so far: {state['results']}\n\n"
        f"And this remaining plan: {state['plan'][state['step_index']:]}\\n\n"
        f"Should we continue, revise the plan, or declare done? Reply with 'CONTINUE', 'REVISE: <new plan>', or 'DONE'."
    )
    if msg.content.startswith("DONE"):
        return {"done": True}
    if msg.content.startswith("REVISE"):
        new_plan = [s.strip() for s in msg.content.split(":", 1)[1].split("\n") if s.strip()]
        return {"plan": new_plan, "step_index": 0}
    return {"done": False}

def route(state: State) -> str:
    return "__end__" if state["done"] else "execute"

g = StateGraph(State)
g.add_node("plan", planner)
g.add_node("execute", executor)
g.add_node("replan", replanner)
g.add_edge(START, "plan")
g.add_edge("plan", "execute")
g.add_edge("execute", "replan")
g.add_conditional_edges("replan", route)
g.add_edge("execute", END)

agent = g.compile()
```

## Evaluation

A golden dataset of 10 multi-step questions. The evaluator checks: (1) the final answer is correct, (2) the agent produced a reasonable plan, (3) the agent did not loop in the replanner more than 3 times.

## Production notes

In production, the planner and replanner are different LLM calls with different prompts - the planner focuses on decomposition, the replanner focuses on adaptation. Tune them separately. The executor is often a ReAct agent (use `create_react_agent` for it). The most common failure: the replanner never declares "done" because it always thinks one more step would help. Fix: add a max-replanning-iteration count.

## Common pitfalls

- Using plan-and-execute for simple tasks. Why: it feels more sophisticated. Fix: use ReAct for tasks under 5 steps.
- Not capping replanning iterations. Why: it works in dev. Fix: cap at 3-5.
- Replanning too aggressively. Why: every unexpected result triggers a full replan. Fix: only replan when the result contradicts the plan's assumptions.

## Further reading

- [Plan-and-Solve prompting](https://arxiv.org/abs/2305.04091)
- [LangGraph plan-and-execute example](https://langchain-ai.github.io/langgraph/tutorials/plan-and-execute/plan-and-execute/)

## Checklist

- [ ] Implement plan-and-execute with planner, executor, and replanner
- [ ] Cap replanning iterations
- [ ] Choose between ReAct and plan-and-execute based on task complexity
- [ ] Use a ReAct agent as the executor
