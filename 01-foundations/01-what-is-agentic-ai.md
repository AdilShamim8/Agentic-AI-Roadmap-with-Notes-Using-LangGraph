# What is agentic AI

Module: 01-foundations
Chapter: 01-what-is-agentic-ai
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

By the end of this chapter, you will be able to:

- Define "agent" precisely enough to distinguish it from a chain and a workflow
- Explain why agency is a spectrum, not a binary, and place real systems on that spectrum
- Identify the four components every agent has (model, tools, memory, loop) and reason about which one is failing when an agent breaks
- Diagnose whether a given problem actually requires an agent or whether a simpler abstraction would do

## Prerequisites

This chapter can be read standalone. No prior LangGraph or LangChain knowledge is required.

## Conceptual foundation

The word "agent" gets used to mean at least four different things in 2026: a chatbot that calls a function, a multi-step LLM pipeline, an LLM that decides which tool to call in a loop, and a fully autonomous system that pursues a goal over hours or days. These are not the same thing, and the confusion costs real engineering time. When someone says "we are building an agent," the first question a senior engineer asks is: which of those four?

The cleanest definition, and the one this roadmap uses, comes from Anthropic's "Building Effective Agents" essay: an agent is a system where an LLM dynamically directs its own processes and tool usage, maintaining control over how it accomplishes a task. The key word is "dynamically." A chain is a fixed sequence of LLM calls. A workflow is a graph of LLM calls with predefined routing. An agent is a system where the LLM itself decides the routing, based on what it observes.

This gives us a spectrum, not a binary. On one end, a single LLM call with no tools is just a model. Add a fixed prompt template and you have a chain. Add conditional routing based on the model's output and you have a workflow. Add a loop where the model decides whether to call a tool, observe the result, and decide again - that is an agent. At the far end, an agent that runs for hours, persists state, calls dozens of tools, and revises its plan based on intermediate results is what people mean when they say "autonomous agent."

The spectrum matters because the failure modes are different at each point. A chain fails when the prompt is wrong. A workflow fails when the routing is wrong. An agent fails when the model picks the wrong tool, calls it with the wrong arguments, misinterprets the result, or loops forever. The engineering techniques for handling each failure mode are different. This is why "just build an agent" is not a useful instruction - the level of agency determines the entire engineering approach.

Every agent, regardless of where it sits on the spectrum, has four components:

1. A model - the LLM that does the reasoning. The choice of model constrains everything else: tool-calling quality, context window, cost, latency.
2. Tools - the functions the agent can call to observe or affect the world. Tools are the agent's hands and eyes.
3. Memory - the state the agent carries across steps. This includes the conversation history, intermediate results, and any long-term knowledge.
4. A loop - the control flow that decides what to do next. The simplest loop is ReAct (reason, act, observe, repeat). More complex loops add planning, reflection, and human approval.

When an agent is failing, the first diagnostic question is: which of these four components is the problem? A model problem shows up as bad reasoning. A tools problem shows up as the agent calling the wrong tool or passing wrong arguments. A memory problem shows up as the agent forgetting context across turns. A loop problem shows up as the agent running forever, terminating too early, or taking a nonsensical path. Diagnosing which component is failing is 80 percent of agent debugging.

The last conceptual point: not every problem requires an agent. If you know the steps in advance, use a workflow. If the steps are fixed but the routing between them depends on the data, use a workflow with conditional edges. Only use an agent when the steps themselves are unknown at design time and must be determined by the LLM based on what it observes. Using an agent when a workflow would do is the single most common architectural mistake in 2026. It costs more, fails more, and is harder to debug.

## Worked example

There is no code in this chapter - it is purely conceptual. The first code you will write is in the next chapter. But to make the spectrum concrete, here are four systems placed on it:

- A summarizer that takes a document and returns a 3-bullet summary is a chain. One LLM call, fixed prompt, no tools.
- A customer-support bot that classifies the message (refund, bug, feature request) and routes to one of three different response generators is a workflow. Multiple LLM calls, conditional routing, no loop.
- A research bot that takes a question, decides whether to search the web, reads results, decides whether to search again, and synthesizes an answer is an agent. The LLM decides the steps based on what it observes.
- A coding agent that takes a failing test, reads the codebase, writes a patch, runs the tests, and iterates until the tests pass is an autonomous agent. It runs for minutes to hours, revises its plan, and persists state.

## Evaluation

There is no eval for this chapter - it is conceptual. The checklist below is the self-test.

## Production notes

The decision of agent vs. workflow vs. chain is the most expensive architectural decision in an agentic AI project, and it is made badly more often than it is made well. The most common failure mode is reaching for an agent because the problem feels complex, when a workflow with three nodes would solve it more reliably at a tenth of the cost. The second most common failure mode is reaching for a workflow when the problem genuinely requires an agent - the workflow grows to fifteen nodes trying to anticipate every routing case, becomes unmaintainable, and gets replaced by a five-line agent that handles the same cases by just letting the LLM decide.

The heuristic: start with a workflow. If you find yourself adding nodes to handle edge cases that all look like "the LLM should just decide," switch to an agent. If you find yourself adding loop guards and reflection to your agent, ask whether a workflow with a fixed retry would be simpler.

## Common pitfalls

- Treating "agent" as a binary. Why: the word is overloaded. Fix: always specify where on the spectrum you mean.
- Reaching for an agent when a workflow would do. Why: agents feel more impressive. Fix: start with a workflow, switch only when you have evidence the workflow cannot handle the case.
- Reaching for a workflow when an agent would do. Why: workflows feel safer. Fix: if your workflow has more than ten nodes, ask whether an agent would be simpler.
- Diagnosing agent failures as model failures. Why: the model is the most visible component. Fix: check tools, memory, and loop first - they are easier to fix than the model.

## Further reading

- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) - Anthropic's essay that defines the spectrum this chapter uses
- [What is an LLM Agent?](https://lilianweng.github.io/posts/2023-06-23-agent/) - Lilian Weng's technical deep-dive on agent architectures
- [ReAct: Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629) - the paper that established the reason-act-observe loop

## Checklist

You understand this chapter if you can:

- [ ] Define "agent" in one sentence and distinguish it from a chain and a workflow
- [ ] Place a real system on the agent spectrum and justify the placement
- [ ] Name the four components of every agent and identify which one is failing given a symptom
- [ ] Decide whether a given problem requires an agent, a workflow, or a chain, and defend the choice
