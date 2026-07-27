# Agent handoffs

Module: 07-multi-agent-and-a2a
Chapter: 02-agent-handoffs
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Implement a handoff that transfers the right context (not too much, not too little)
- Decide when to reset state on handoff (full reset, partial reset, no reset)
- Handle handoff failures (target agent unavailable, target agent rejects the task)
- Use `langgraph-swarm`'s handoff tools and `langgraph-supervisor`'s delegation

## Prerequisites

- [01 Multi-agent architectures](01-multi-agent-architectures.md)

## Conceptual foundation

A handoff is the moment when one agent passes control to another. The handoff has three parts: the trigger (when to hand off), the context (what to pass), and the recovery (what to do if the handoff fails). All three must be designed explicitly; leaving any to chance produces failures.

The trigger. When does an agent hand off? Three patterns:

1. Explicit. The agent's prompt says "hand off to the writer when you have collected enough research." The agent itself decides. This is the swarm pattern.

2. Router. A separate supervisor LLM decides who should handle the next step. The agents themselves do not decide. This is the supervisor pattern.

3. Capability-based. The agent tries to handle the task, and if it cannot (a required tool is missing, or a validator fails), it hands off. This is the fallback pattern.

The context. What does the receiving agent see? Three options:

1. Full history. The receiving agent sees the entire conversation. Pro: no context loss. Con: context bloat, especially after multiple handoffs.

2. Summary. The handing-off agent produces a summary of the conversation so far, and the receiving agent sees only the summary. Pro: bounded context. Con: information loss in the summary.

3. Structured handoff. The handing-off agent produces a structured handoff message: what was requested, what was done, what the receiving agent should do next. Pro: explicit and bounded. Con: requires the handing-off agent to produce a good handoff message.

The structured handoff is usually the right choice. It forces the handing-off agent to be explicit about what the receiving agent needs to know, and it bounds the context the receiving agent has to process.

The recovery. What if the handoff fails?

1. Target unavailable. The target agent is down or unresponsive. Fix: fall back to a generalist agent, or return an error to the user.

2. Target rejects. The target agent says "this is not my area." Fix: route to a different agent, or escalate to a human.

3. Target loops. The target agent hands back to the source, which hands back to the target. Fix: track handoff history and refuse to hand off to an agent that has already been tried.

## Worked example

A structured handoff between a researcher and a writer. Full code in [`examples/handoff_demo.py`](../examples/handoff_demo.py).

```python
from langgraph_swarm import create_handoff_tool
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

researcher = create_react_agent(
    llm,
    tools=[create_handoff_tool("writer")],
    prompt="""You are a research specialist. When you have collected enough
    research to answer the user's question, hand off to the writer with a
    structured message:

    RESEARCH_COMPLETE
    Question: <the user's question>
    Key findings:
    - <finding 1>
    - <finding 2>
    - <finding 3>
    Recommended structure for the answer: <suggestion>

    Do not hand off until you have at least 3 key findings.
    """,
)

writer = create_react_agent(
    llm,
    tools=[],
    prompt="""You are a writer. You receive a RESEARCH_COMPLETE message from
    the researcher. Write the answer based on the findings. Do not do your
    own research; use only what the researcher provided.
    """,
)
```

## Evaluation

The eval checks: (1) the handoff message contains the required fields, (2) the receiving agent does not re-do work the handing-off agent already did, (3) the handoff count is reasonable (no loops).

## Production notes

In production, handoffs are the most common failure point in multi-agent systems. The defenses: log every handoff with the full handoff message (so you can debug what the receiving agent received), track handoff count per request and alert if it grows, and have a fallback for every handoff (what to do if the target is unavailable). The most common production failure: the handing-off agent produces a vague handoff message ("here is what I found, you take it from here") and the receiving agent has to re-do the work. The fix: enforce a structured handoff format and validate it.

## Common pitfalls

- Full history handoffs. Why: it is the default. Fix: use structured handoffs to bound context.
- No handoff validation. Why: it works in dev. Fix: validate the handoff message has the required fields.
- No handoff loop detection. Why: rare in dev. Fix: track handoff history; refuse to re-handoff.

## Further reading

- [langgraph-swarm: handoffs](https://github.com/langchain-ai/langgraph-swarm-py)
- [OpenAI Agents SDK: handoffs](https://openai.github.io/openai-agents-python/handoffs/)

## Checklist

- [ ] Implement a structured handoff with explicit fields
- [ ] Choose between full history, summary, and structured handoff based on context size
- [ ] Handle handoff failures (target unavailable, target rejects, loops)
- [ ] Log every handoff with the full handoff message
