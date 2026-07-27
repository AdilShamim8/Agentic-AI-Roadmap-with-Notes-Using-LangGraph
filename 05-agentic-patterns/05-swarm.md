# Swarm

Module: 05-agentic-patterns
Chapter: 05-swarm
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement the swarm pattern: agents hand off to each other peer-to-peer, no central supervisor
- Use `langgraph-swarm` for the standard implementation
- Diagnose swarm failure modes (handoff loops, lost context, unbounded handoffs)
- Choose between swarm and supervisor based on task structure

## Prerequisites

- [04 Supervisor](04-supervisor.md)

## Conceptual foundation

The swarm pattern is the peer-to-peer alternative to the supervisor pattern. There is no central router. Each agent can hand off to any other agent directly, based on its own judgment. The handoff is a tool call: the agent calls a `transfer_to_<other_agent>` tool, which transfers control to the other agent along with the conversation context.

The pattern was popularized by OpenAI's Agents SDK and is implemented in LangGraph by `langgraph-swarm`. It is the right choice when:

- The task does not have a clear "router" structure (any agent might need to hand off to any other)
- The agents are roughly peers (no clear hierarchy)
- The handoff decision is local (each agent knows when it has hit the limit of its expertise)

Swarm fails when:

- Agents hand off to each other in a loop (A hands to B, B hands to A, repeat)
- The handoff loses context (the receiving agent does not have enough information to continue)
- The handoff is too frequent (every agent hands off after one turn, no one does substantive work)

The fix for all three: clear handoff criteria. Each agent's prompt should specify when to hand off ("hand off to the writer when you have collected enough research") and when not to ("do not hand off if you can answer the question yourself").

## Worked example

A swarm of three agents: researcher, analyst, writer. Each can hand off to the others. Full code in [`examples/swarm_demo.py`](../examples/swarm_demo.py).

```python
from langgraph_swarm import create_swarm, create_handoff_tool
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

llm = ChatOpenAI(model="gpt-4o", temperature=0)

@tool
def search_web(query: str) -> str:
    """Search the web."""
    return f"[Results: {query}]"

@tool
def analyze(data: str) -> str:
    """Analyze data."""
    return f"[Analysis: {data}]"

@tool
def write(content: str) -> str:
    """Write a report."""
    return f"# Report\n{content}"

# Each agent can hand off to the others
researcher = create_react_agent(
    llm, tools=[search_web, create_handoff_tool("analyst"), create_handoff_tool("writer")],
    prompt="You research. Hand off to analyst when you have data, to writer when research is done.",
)
analyst = create_react_agent(
    llm, tools=[analyze, create_handoff_tool("researcher"), create_handoff_tool("writer")],
    prompt="You analyze. Hand off to researcher if you need more data, to writer when analysis is done.",
)
writer = create_react_agent(
    llm, tools=[write, create_handoff_tool("researcher"), create_handoff_tool("analyst")],
    prompt="You write. Hand off to researcher if you need more info, to analyst if you need analysis.",
)

swarm = create_swarm(
    [researcher, analyst, writer],
    default_active_agent="researcher",
)
app = swarm.compile()
```

## Evaluation

Same as supervisor: a golden dataset of 10 multi-step tasks. The evaluator checks correctness, handoff count, and that no handoff loops occurred.

## Production notes

In production, swarm is harder to debug than supervisor because there is no central decision point. The trace shows a sequence of handoffs, but the rationale for each handoff is inside the agent that made it. The defenses: log every handoff with the rationale (the agent should output why it is handing off), cap the total handoff count, and alert on handoff loops.

## Common pitfalls

- No handoff criteria in agent prompts. Why: the LLM hands off randomly. Fix: specify when to hand off and when not to.
- No handoff cap. Why: it works in dev. Fix: cap at 10.
- Choosing swarm when supervisor would do. Why: swarm feels more flexible. Fix: use supervisor when there is a clear router structure; swarm is for genuinely peer-to-peer tasks.

## Further reading

- [langgraph-swarm](https://github.com/langchain-ai/langgraph-swarm-py)
- [OpenAI Swarm](https://github.com/openai/swarm)

## Checklist

- [ ] Implement a swarm of 3+ agents with handoff tools
- [ ] Specify handoff criteria in each agent's prompt
- [ ] Cap total handoffs
- [ ] Log every handoff with the rationale
