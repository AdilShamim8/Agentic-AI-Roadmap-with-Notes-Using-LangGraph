# Coding rounds

Module: interview
Chapter: 02-coding-rounds
Status: stable
Last reviewed: 2026-07-27
Estimated time: 1 hour

## What is asked

The agentic AI engineer coding round is usually one of:

1. Implement a LangGraph agent from a spec. "Build a ReAct agent with a calculator tool and a web search tool. Include a max-iteration limit and error handling."
2. Implement a tool. "Build a tool that queries a SQLite database. Include schema validation and error handling."
3. Implement an evaluator. "Build an LLM-as-judge evaluator for answer quality."
4. Debug an existing agent. "Here is an agent that is failing. Find the bug and fix it."

The expectations: working code, type hints, docstrings, error handling, at least one test. The code follows the patterns in this curriculum (StateGraph, ToolNode, Pydantic schemas).

## How to prepare

- Build the [projects](../projects/). At least 2-3 of them. The take-home and the coding round test the same skills.
- Read the [examples](../examples/) in this repo. They are reference implementations of the core patterns.
- Practice implementing an agent from a spec in 30 minutes. Time yourself. The coding round is usually 45-60 minutes, including discussion.
- Memorize the boilerplate: how to define a StateGraph, how to use `create_react_agent`, how to write a tool with `@tool`, how to use `interrupt()`. You should not be looking these up during the interview.

## A worked example

Prompt: "Build a ReAct agent with a calculator tool. The agent should answer math questions. Include a max-iteration limit of 5 and error handling for invalid expressions."

Expected solution (10-15 minutes):

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression. Input should be a valid Python expression
    like '2 + 2' or 'sin(3.14)'. Returns the result as a string, or an error
    message if the expression is invalid.

    Use this tool for any arithmetic or math question. Do not use it for
    non-math questions.
    """
    try:
        # Restrict builtins for safety
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating '{expression}': {e}. Try a different expression."

def build_agent():
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    agent = create_react_agent(
        llm,
        tools=[calculator],
        recursion_limit=5,
    )
    return agent

# Test
if __name__ == "__main__":
    agent = build_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": "What is 2 + 2?"}]})
    print(result["messages"][-1].content)
```

What the interviewer is checking:

- Did you use `@tool` and write a clear description? (Tool design skill.)
- Did you set a recursion limit? (Production awareness.)
- Did you handle errors in the tool? (Robustness.)
- Did you write a docstring? (Communication.)
- Did you write a test? (Engineering discipline.)

## Common mistakes

- No error handling in the tool. The agent crashes on invalid input.
- No recursion limit. The agent loops forever on a confused model.
- No docstring on the tool. The interviewer cannot tell what the tool does.
- Not using `@tool`. Writing the tool as a plain function and trying to bind it manually.
- Over-complicating. A custom StateGraph when `create_react_agent` would do.

## Further reading

- [01 Foundations: Structured outputs and tools](../01-foundations/05-structured-outputs-and-tools.md)
- [03 Agents in practice](../03-agents-in-practice/)
- [examples/](../examples/) for reference implementations
