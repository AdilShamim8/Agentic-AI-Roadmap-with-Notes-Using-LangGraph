# Streaming and UX

Module: 03-agents-in-practice
Chapter: 05-streaming-and-ux
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Stream tokens from an LLM through a LangGraph agent to a client
- Stream events (node starts, tool calls, tool results) for UI updates
- Choose between token streaming and event streaming based on UX needs
- Build a streaming frontend that handles backpressure and partial states

## Prerequisites

- [01 Conversational agents](01-conversational-agents.md)

## Conceptual foundation

Streaming is the difference between an agent that feels fast (tokens appear as they are generated) and one that feels slow (the user waits 10 seconds for a complete response). For conversational agents, token streaming is table stakes in 2026. For agents with tools, event streaming (the UI shows "calling web_search..." while the tool runs) is what makes the agent feel transparent rather than magical.

LangGraph supports three streaming modes:

1. `values` - streams the full state after each node execution. Coarse-grained; useful for debugging.
2. `updates` - streams the diff after each node execution. Medium-grained; useful for showing progress.
3. `messages` - streams individual tokens from the LLM. Fine-grained; this is what you want for a chat UI.

You can stream all three simultaneously. The typical pattern: stream `messages` for the chat UI (tokens appear as they are generated), stream `updates` for a sidebar that shows which node is running, and use `values` only for debugging.

The UX considerations:

- Token streaming should start within 1 second of the user's message. If it takes longer, show a "thinking..." indicator so the user knows the agent is working.
- Tool calls should be visible to the user (as "Searching the web..." or "Looking up order ABC123..."). Hidden tool calls feel like magic, which is bad - magic is unpredictable.
- Errors should be visible and recoverable. If a tool fails, the UI should show the error and the agent's recovery (if any).

## Worked example

A streaming chat client that prints tokens as they arrive and shows tool-call events. Full code in [`examples/streaming_demo.py`](../examples/streaming_demo_demo.py).

```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

@tool
def get_weather(location: str) -> str:
    """Get current weather."""
    return f"72F, sunny in {location}"

llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
agent = create_react_agent(llm, tools=[get_weather], checkpointer=MemorySaver())

config = {"configurable": {"thread_id": "stream-1"}}

# Stream tokens and events
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What's the weather in SF?"}]},
    config=config,
    stream_mode="updates",
):
    for node_name, node_output in chunk.items():
        print(f"[{node_name}]")
        if "messages" in node_output:
            for msg in node_output["messages"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for call in msg.tool_calls:
                        print(f"  -> calling tool: {call['name']}({call['args']})")
                elif msg.content:
                    print(f"  -> {msg.content[:100]}")
```

For a true token-level stream (each token printed as it arrives), use `stream_mode="messages"` and iterate over the chunks - each chunk contains a single token.

## Evaluation

Streaming is a UX feature, not a correctness feature, so the eval is the same as for the underlying agent. The streaming-specific test is a latency test: time-to-first-token should be under 1 second for 95 percent of requests.

## Production notes

In production, streaming has three concerns: backpressure (the client must consume tokens at least as fast as the server produces them, or the server's buffer grows), connection management (if the client disconnects mid-stream, the server should stop generating), and observability (you need to log the stream events to diagnose "the agent felt slow" reports). For web frontends, Server-Sent Events (SSE) is the standard transport; LangGraph Platform supports this out of the box.

## Common pitfalls

- Not streaming tokens. Why: it works without it. Fix: stream tokens; the UX improvement is large.
- Hiding tool calls from the user. Why: it looks cleaner. Fix: show tool calls; transparency builds trust.
- Not handling client disconnect. Why: it works in dev. Fix: detect disconnect and stop generation.

## Further reading

- [LangGraph streaming](https://langchain-ai.github.io/langgraph/how-tos/streaming-tokens/)
- [LangGraph streaming modes](https://langchain-ai.github.io/langgraph/concepts/streaming/)

## Checklist

- [ ] Stream tokens from an LLM through a LangGraph agent
- [ ] Stream events for a tool-call progress UI
- [ ] Show tool calls to the user in the UI
- [ ] Handle client disconnect mid-stream
