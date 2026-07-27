# Iterative workflows

Module: 02-langgraph-core
Chapter: 05-iterative-workflows
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Build a graph with a cycle (loop back to an earlier node)
- Implement a generator-critic loop with a termination condition
- Add a max-iteration guard to prevent infinite loops
- Choose between iterative refinement and one-shot generation

## Prerequisites

- [01 Graph, state, edges, nodes](01-graph-state-edges-nodes.md)
- [04 Conditional workflows](04-conditional-workflows.md)

## Conceptual foundation

An iterative workflow is a graph with a cycle: node A produces output, node B evaluates it, and if B is not satisfied the graph routes back to A with feedback. This is the simplest form of reflexion, and it is one of the most effective patterns for improving LLM output quality. A single retry with structured feedback fixes a large fraction of failures that one-shot generation gets wrong.

The components of an iterative workflow:

1. A generator node that produces output (an essay, a code patch, a response).
2. A critic node that evaluates the output and produces structured feedback.
3. A conditional edge that routes back to the generator (with the feedback) or to `END` (if the critic is satisfied or the max iteration is reached).
4. A state field that tracks the iteration count.
5. A termination condition: critic satisfied, or iteration count exceeds the limit.

The termination condition is the most important part. Without it, the loop runs forever. The two termination conditions are: the critic signals satisfaction (a boolean field set by the critic), or the iteration count exceeds a hard limit (5 to 10 is typical). Both should be present - the critic satisfaction is the "happy path" and the iteration limit is the safety net.

Iterative workflows are more expensive than one-shot generation (each iteration is an LLM call), so the question is when the quality improvement justifies the cost. The answer depends on the cost of a bad output. For a tweet generator, one-shot is fine. For a code patch that will be merged to main, three iterations of generate-critique-regenerate is cheap insurance. For a legal document, ten iterations might be worth it.

## Worked example

An X/Twitter post generator: generate a post, critique it for engagement and tone, regenerate if the critique is negative, max 3 iterations. Full code in [`examples/iterative_workflow_demo.py`](../examples/iterative_workflow_demo.py).

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

class State(TypedDict):
    topic: str
    post: str
    feedback: str
    satisfied: bool
    iteration: int

def generate(state: State) -> dict:
    prompt = f"Write an engaging X post about: {state['topic']}."
    if state.get("feedback"):
        prompt += f"\n\nPrevious attempt:\n{state['post']}\n\nFeedback:\n{state['feedback']}\n\nWrite a better version."
    msg = llm.invoke(prompt)
    return {"post": msg.content, "iteration": state["iteration"] + 1}

def critique(state: State) -> dict:
    msg = llm.invoke(
        f"Critique this X post for engagement and tone. "
        f"Reply with 'GOOD' or 'BAD: <reason>'.\n\n{state['post']}"
    )
    content = msg.content
    satisfied = content.startswith("GOOD")
    feedback = "" if satisfied else content
    return {"satisfied": satisfied, "feedback": feedback}

def should_continue(state: State) -> str:
    if state["satisfied"]:
        return "__end__"
    if state["iteration"] >= 3:
        return "__end__"
    return "generate"

g = StateGraph(State)
g.add_node("generate", generate)
g.add_node("critique", critique)
g.add_edge(START, "generate")
g.add_edge("generate", "critique")
g.add_conditional_edges("critique", should_continue)
g.add_edge("generate", END)  # not used; here for clarity

agent = g.compile()
result = agent.invoke({"topic": "agentic AI", "post": "", "feedback": "", "satisfied": False, "iteration": 0})
```

## Evaluation

A golden dataset of 10 topics. The evaluator checks that the final post is under 280 characters, mentions the topic, and that the loop terminated (did not exceed 3 iterations).

## Production notes

In production, iterative workflows have a cost ceiling. Each iteration is one or more LLM calls, and the cost compounds. Track the average iteration count and alert if it drifts upward (a sign that the generator or critic is degrading). Set a hard max-iteration limit and log when it is hit. Consider a budget-based termination: stop iterating when the cumulative cost exceeds a threshold.

## Common pitfalls

- No iteration limit. Why: it works in dev when the critic eventually says GOOD. Fix: always have a hard limit.
- Critic that never says GOOD. Why: the critic prompt is too strict. Fix: calibrate the critic with examples of acceptable output, or change the critic to score on a scale and accept anything above a threshold.
- Generator that ignores the feedback. Why: the feedback is vague. Fix: require the critic to produce specific, actionable feedback, and include the previous attempt in the generator's prompt.

## Further reading

- [Reflexion paper](https://arxiv.org/abs/2303.11366)
- [LangGraph cycles](https://langchain-ai.github.io/langgraph/concepts/low_level/#cycles)

## Checklist

- [ ] Build a generator-critic loop with a max-iteration guard
- [ ] Add a critic-satisfaction termination condition
- [ ] Track the average iteration count over a golden dataset
- [ ] Decide between iterative refinement and one-shot generation for a given task
