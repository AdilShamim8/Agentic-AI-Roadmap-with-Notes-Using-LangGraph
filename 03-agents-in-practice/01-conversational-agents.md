# Conversational agents

Module: 03-agents-in-practice
Chapter: 01-conversational-agents
Status: stable
Last reviewed: 2026-07-27
Estimated time: 3 hours

## Learning objectives

- Build a conversational agent with the message-state pattern and `add_messages` reducer
- Manage multi-turn context (summarization, trimming, sliding window)
- Use `create_react_agent` for the standard ReAct loop
- Diagnose the three common conversational-agent failure modes (lost context, tool-call loops, persona drift)

## Prerequisites

- [02 LangGraph core](../02-langgraph-core/)

## Conceptual foundation

A conversational agent is an agent whose state is a list of messages. The user sends a message, the agent appends it to the list, the LLM reads the whole list and either responds (append an assistant message) or calls a tool (append a tool-call message, execute the tool, append a tool-result message, re-invoke the LLM). The loop continues until the LLM responds without a tool call.

The `add_messages` reducer is the key piece. It concatenates lists of messages, so each node can return `{"messages": [new_message]}` and the reducer appends it to the existing list. Without this reducer, each node would overwrite the message history instead of appending to it.

The standard pattern is `create_react_agent(llm, tools)`, which gives you a pre-built ReAct loop. For most conversational agents, this is the right starting point. You drop to a custom StateGraph only when you need to add nodes that `create_react_agent` does not support (a separate critic, a human-approval step, a custom router).

Context management is the production concern. Every turn adds messages, and every LLM call re-sends the entire history. A 20-turn conversation with tool calls can easily hit 10K tokens of context. The three strategies:

1. Sliding window: keep only the last N messages. Simple, but loses early context.
2. Summarization: every K turns, summarize the older turns into a single message. Preserves information at lower token cost.
3. Trimming: keep the system prompt and the last N tokens of conversation. More precise than sliding window but harder to implement.

For most production agents, summarization is the right choice. The summary node runs periodically (every 10 turns, or when the context exceeds a threshold), produces a summary message, and the older messages are dropped.

## Worked example

A basic conversational agent with a weather tool, using `create_react_agent`. Full code in [`examples/conversational_agent_demo.py`](../examples/conversational_agent_demo.py).

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

@tool
def get_weather(location: str) -> str:
    """Get current weather for a location. Use when the user asks about weather."""
    return f"72F, sunny in {location}"

llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent = create_react_agent(llm, tools=[get_weather], checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "user-001"}}
# Turn 1
r1 = agent.invoke({"messages": [{"role": "user", "content": "What's the weather in SF?"}]}, config=config)
print(r1["messages"][-1].content)

# Turn 2 - the agent remembers the previous turn
r2 = agent.invoke({"messages": [{"role": "user", "content": "What about Tokyo?"}]}, config=config)
print(r2["messages"][-1].content)
```

The `thread_id` is what ties turns together. The checkpointer stores the message list keyed by thread ID, so the second `invoke` continues the same conversation.

## Evaluation

A golden dataset of 10 multi-turn conversations. The evaluator checks that the agent calls the right tool, that it remembers context from earlier turns (e.g., "what about Tokyo?" should produce a weather call for Tokyo, not ask "Tokyo where?"), and that the response is non-empty.

## Production notes

In production, the dominant cost is the conversation history being re-sent on every turn. Track the average context size per turn and alert when it grows. Implement summarization before cost becomes a problem, not after. The second production concern is tool-call loops: a confused agent calls the same tool repeatedly with the same arguments. The defense is `create_react_agent`'s `recursion_limit` parameter (default 25; set it to 5-10 for production).

## Common pitfalls

- Forgetting the `add_messages` reducer. Why: state seems to work without it. Fix: always annotate messages with `Annotated[list, add_messages]` in custom StateGraphs.
- Not setting a recursion limit. Why: it works in dev. Fix: set it, always.
- Not managing context. Why: short conversations hide the problem. Fix: implement summarization from day one.

## Further reading

- [LangGraph `create_react_agent`](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/)
- [LangGraph message state](https://langchain-ai.github.io/langgraph/concepts/low_level/#state)

## Checklist

- [ ] Build a conversational agent with `create_react_agent` and a checkpointer
- [ ] Use `thread_id` to maintain multi-turn context
- [ ] Set a recursion limit appropriate for production
- [ ] Implement summarization for long conversations
