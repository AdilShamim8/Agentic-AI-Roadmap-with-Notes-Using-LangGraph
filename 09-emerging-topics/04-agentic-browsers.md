# Agentic browsers

Module: 09-emerging-topics
Chapter: 04-agentic-browsers
Status: draft
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Reason about agentic browsers: LLMs that navigate and interact with web pages
- Identify the components (perception, action, state management)
- Reason about the current state (what works, what does not)
- Reason about the trajectory (what will be production-ready in 12-18 months)

## Prerequisites

- [04 Tools and MCP](../04-tools-and-mcp/)

## Conceptual foundation

An agentic browser is an LLM that can navigate web pages: click buttons, fill forms, read content, follow links. The browser becomes the agent's interface to the web, replacing fixed web-scraping tools with a general-purpose web-interaction capability.

The components:

1. Perception. The agent must "see" the page. Approaches: screenshot + vision model, accessibility tree, DOM text. Each has trade-offs (vision is general but slow; accessibility tree is fast but loses visual context; DOM text is fast but loses layout).

2. Action. The agent must act on the page (click, type, scroll, navigate). The action space is small but the choice of action is hard - the agent must decide which element to click based on its perception.

3. State management. The agent must track where it is in a multi-step flow (login, search, click result, extract data). The state is the page's DOM plus the agent's history.

The current state (2026):

- Production-ready for narrow, well-defined tasks (log in and download a specific report; fill a known form). Tools: browser-use, Playwright with LLM-driven selectors.
- Emerging for broad tasks (research a topic across multiple sites; comparison shop). The agent makes too many wrong clicks for unattended use.
- Research-grade for fully autonomous browsing (the agent pursues a high-level goal across arbitrary sites).

The trajectory: agentic browsers are improving fast. The vision models are getting better at understanding pages; the action selection is getting more reliable. By 2027, expect production-ready broad-task browsing. By 2028, expect unattended browsing for well-scoped goals.

## Worked example

No code - this chapter is forward-looking. The exercise: pick a web task you do regularly (check a bank balance, book a flight). Could an agentic browser do it? What would go wrong? What would the agent need to learn the task?

## Evaluation

No eval. The benchmarks for agentic browsing are emerging (WebArena, VisualWebArena); track the state of the art there.

## Production notes

In production (in 2026), use agentic browsers for narrow, well-defined tasks. Do not use them unattended for high-stakes tasks (financial transactions, healthcare). The pattern that works: the agent proposes the next action, a human approves, the agent executes. This is HITL applied to browsing.

## Further reading

- [browser-use](https://github.com/browser-use/browser-use)
- [Claude Computer Use](https://www.anthropic.com/news/3-5-models-and-computer-use)
- [WebArena](https://webarena.dev/)

## Checklist

- [ ] Name the three components of an agentic browser
- [ ] Reason about which browsing tasks are production-ready
- [ ] Design a HITL workflow for agentic browsing
