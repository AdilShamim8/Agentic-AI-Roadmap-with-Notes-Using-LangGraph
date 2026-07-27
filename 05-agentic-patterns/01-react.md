# ReAct

Module: 05-agentic-patterns
Chapter: 01-react
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement the ReAct loop (reason, act, observe) as a LangGraph StateGraph
- Use `create_react_agent` and explain what it does internally
- Diagnose ReAct failure modes (infinite tool loops, wrong tool selection, premature termination)
- Choose between ReAct and one-shot generation based on task complexity

## Prerequisites

- [04 Tools and MCP](../04-tools-and-mcp/)

## Conceptual foundation

ReAct (Reason + Act) is the foundational agent pattern, introduced in a 2022 paper by Yao et al. The idea is simple: the LLM reasons about what to do, takes an action (calls a tool), observes the result, and repeats until it can answer. The reasoning is explicit - the model writes out its thinking before each tool call - which makes the agent's behavior inspectable and debuggable.

The loop has four steps:

1. Reason. The LLM looks at the conversation so far and decides what to do next. In modern implementations, the reasoning is implicit in the tool-call decision - the LLM either calls a tool (with arguments that reflect its reasoning) or responds with text (which is the answer).

2. Act. The LLM calls a tool. The tool executes and returns a result.

3. Observe. The tool result is appended to the conversation as a tool message.

4. Repeat. The LLM looks at the updated conversation and decides what to do next. If it has enough information, it responds with text (the answer). If not, it calls another tool.

The termination conditions: the LLM responds with text (no tool call), or a max-iteration limit is hit. The max-iteration limit is essential - without it, a confused LLM can call the same tool with the same arguments forever.

ReAct is the default pattern for most agents. It is what `create_react_agent` implements. It is the right choice when:

- The task requires multiple tool calls (otherwise, use a single tool call)
- The order of tool calls depends on the results of previous calls (otherwise, use parallel execution)
- The task is not so complex that it requires explicit planning (otherwise, use plan-and-execute)

ReAct fails when:

- The task requires many steps (the LLM loses track of the goal after 5-10 tool calls)
- The tool list is large (selection accuracy degrades with more than 10 tools)
- The task requires backtracking (ReAct does not naturally revisit earlier decisions)

For these cases, use plan-and-execute, reflexion, or a supervisor pattern.

## Worked example

A ReAct agent that answers questions using a web search tool and a calculator. Full code in [`examples/react_demo.py`](../examples/react_demo.py).

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

@tool
def web_search(query: str) -> str:
    """Search the web for current information. Use when the question requires
    up-to-date information or facts not in your training data."""
    return f"[Search results for: {query}]"

@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression. Use for any arithmetic or calculation.
    Input should be a valid Python expression like '2 + 2' or 'sin(3.14)'."""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"

llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent = create_react_agent(llm, tools=[web_search, calculator])

result = agent.invoke({
    "messages": [{"role": "user", "content": "What is the population of Tokyo times 2?"}]
})
print(result["messages"][-1].content)
```

The agent will: call `web_search("Tokyo population")`, observe the result, call `calculator("<population> * 2")`, observe the result, and respond with the answer.

## Evaluation

A golden dataset of 20 questions, each requiring one or two tool calls. The evaluator checks: (1) the final answer is correct, (2) the agent called the right tools in the right order, (3) the agent did not exceed 5 tool calls.

## Production notes

In production, the `recursion_limit` parameter on `create_react_agent` is your safety net. The default is 25, which is too high for most production agents - set it to 5-10. Track the average number of tool calls per request and alert if it drifts upward (a sign of degradation). For long-running ReAct agents (more than 10 tool calls), consider switching to plan-and-execute - the explicit plan keeps the agent on track.

## Common pitfalls

- Not setting a recursion limit. Why: it works in dev. Fix: set it to 5-10 for production.
- Using ReAct for tasks that require explicit planning. Why: it works for 3-step tasks. Fix: switch to plan-and-execute for tasks with more than 5 steps.
- Too many tools. Why: more tools feels more capable. Fix: keep under 10 tools per agent; use a supervisor to route to specialist agents with fewer tools each.

## Further reading

- [ReAct paper](https://arxiv.org/abs/2210.03629)
- [LangGraph `create_react_agent`](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/)

## Checklist

- [ ] Implement a ReAct agent with `create_react_agent` and at least 2 tools
- [ ] Set a recursion limit appropriate for production
- [ ] Track the average number of tool calls per request
- [ ] Decide between ReAct and plan-and-execute based on task complexity
