# Roadmap

The six-phase path through the curriculum. Each phase has a status badge, a goal, and the modules it covers.

Status legend: `done` — content shipped and reviewed. `beta` — content shipped, undergoing review. `draft` — content in progress. `planned` — spec only.

## Phase 1 — Foundations `done`

Goal: build a rock-solid base in LLMs, prompt engineering, and the LangChain ecosystem. Understand what an agent is and why LangGraph exists.

Modules: [01-foundations](01-foundations/)

Time: 2 to 3 weeks at 2 to 3 hours per day.

What you will be able to do:

- Explain the difference between a chain, a workflow, and an agent, and choose the right abstraction for a given problem
- Call OpenAI and Anthropic APIs with structured outputs and tool calls
- Write a prompt that produces reliable structured output across model providers
- Diagnose common LLM failure modes (context window exhaustion, prompt injection, schema drift)

Checkpoint: build a structured-output Q&A bot that calls a tool, with a 20-row golden dataset and an exact-match evaluator.

## Phase 2 — LangGraph core mastery `done`

Goal: deep mastery of LangGraph's architecture and both API surfaces (StateGraph and Functional).

Modules: [02-langgraph-core](02-langgraph-core/)

Time: 3 to 4 weeks.

What you will be able to do:

- Model any multi-step LLM workflow as a graph: nodes, edges, conditional edges, reducers
- Choose between StateGraph and the Functional API based on the problem shape
- Implement parallel fan-out and fan-in with correct state reduction
- Implement iterative loops with termination conditions and cycle guards
- Persist and resume execution with checkpointers

Checkpoint: rebuild the Phase 1 bot as a LangGraph StateGraph, then rebuild it again using the Functional API. Both must pass the same eval suite.

## Phase 3 — Agents in practice `done`

Goal: build, debug, and deploy real single-agent systems that handle tools, memory, human approvals, and streaming.

Modules: [03-agents-in-practice](03-agents-in-practice/)

Time: 3 weeks.

What you will be able to do:

- Build a conversational agent with persistent cross-session memory
- Integrate external tools (APIs, databases, file systems) with proper error handling
- Add human-in-the-loop approval workflows using `interrupt()` and `Command(resume=...)`
- Stream tokens and events to a frontend
- Debug a running agent in LangGraph Studio

Checkpoint: a customer-support-style agent that uses two tools, persists conversation state across sessions, requires human approval before executing a side-effecting tool, and streams responses to a terminal client.

## Phase 4 — Tools and MCP `beta`

Goal: master tool design as a first-class skill and the Model Context Protocol as the standard tool interop layer.

Modules: [04-tools-and-mcp](04-tools-and-mcp/)

Time: 2 to 3 weeks.

What you will be able to do:

- Design tool schemas and descriptions that produce reliable tool selection
- Build an MCP server from scratch in Python using the `mcp` SDK
- Consume MCP servers from a LangGraph agent via `langchain-mcp-adapters`
- Implement dynamic tool discovery from a registry

Checkpoint: build two MCP servers (filesystem, web search), consume them from a single LangGraph agent, and benchmark tool-selection accuracy on a 30-row golden dataset.

## Phase 5 — Agentic patterns `beta`

Goal: master the canonical agent architectures and the decision framework for choosing between them.

Modules: [05-agentic-patterns](05-agentic-patterns/)

Time: 3 to 4 weeks.

What you will be able to do:

- Implement ReAct, plan-and-execute, reflexion, supervisor, swarm, hierarchical, and map-reduce patterns
- Diagnose which pattern fits a given problem based on task structure, tool count, and reliability requirements
- Identify the failure modes unique to each pattern and the mitigations

Checkpoint: implement the same task (research-and-write-a-report) using three different patterns, run all three against the same eval suite, and write a one-page analysis of the trade-offs.

## Phase 6 — Evals and observability `draft`

Goal: build the discipline that separates professionals from hobbyists. Every agent you ship has an eval suite that runs in CI.

Modules: [06-evals-and-observability](06-evals-and-observability/)

Time: 2 to 3 weeks.

What you will be able to do:

- Build a golden dataset from production samples and adversarial cases
- Implement an LLM-as-judge evaluator with a versioned rubric
- Instrument an agent with LangSmith tracing and read the traces
- Track cost and latency distributions and alert on regressions
- Run the eval suite as a CI gate that blocks PRs on regressions

Checkpoint: take any agent from Phase 3, 4, or 5, build a 50-row golden dataset, implement three evaluators (rule-based, LLM-as-judge, trajectory), and wire the suite into GitHub Actions.

## Phase 7 — Multi-agent and A2A `draft`

Goal: scale from single-agent to multi-agent systems using both LangGraph's native patterns and the A2A protocol for cross-framework interop.

Modules: [07-multi-agent-and-a2a](07-multi-agent-and-a2a/)

Time: 3 weeks.

What you will be able to do:

- Architect multi-agent systems using supervisor, swarm, and hierarchical patterns
- Implement agent handoffs with correct context transfer
- Expose a LangGraph agent as an A2A server with an Agent Card
- Consume an A2A agent from a different framework (OpenAI Agents SDK, CrewAI)

Checkpoint: build a cross-framework pipeline where a LangGraph supervisor delegates to one OpenAI Agents SDK agent and one CrewAI agent, both consumed via A2A.

## Phase 8 — Production `draft`

Goal: deploy, monitor, and scale agentic systems that run in production.

Modules: [08-production](08-production/)

Time: 3 to 4 weeks.

What you will be able to do:

- Deploy a LangGraph agent to LangGraph Platform or self-hosted Docker
- Configure checkpointing for durable execution
- Optimize cost with model routing and token budgeting
- Implement governance: permissioned tools, audit logs, PII handling
- Set up continuous improvement with feedback loops and A/B testing

Checkpoint: deploy the Phase 3 agent to Docker with a Postgres checkpointer, wire it to LangSmith, and ship a one-page runbook for on-call.

## Phase 9 — Emerging topics `draft`

Goal: track the frontier. Understand where the field is going so your skills stay current.

Modules: [09-emerging-topics](09-emerging-topics/)

Time: ongoing.

What you will be able to do:

- Reason about agent OS and kernel designs
- Diagnose the long-horizon memory problem and the current best answers
- Evaluate autonomous SDLC and agentic browser systems
- Identify the safety and alignment challenges specific to agentic systems

Checkpoint: write a one-page position paper on which emerging topic will have the largest production impact in the next 18 months, with evidence.
