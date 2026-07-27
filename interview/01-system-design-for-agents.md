# System design for agents

Module: interview
Chapter: 01-system-design-for-agents
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## What this chapter covers

The system design round is the most distinctive part of an agentic AI engineer interview. This chapter walks through three worked examples and the framework for answering any agent system design question.

## The framework

Every agent system design answer should cover six areas:

1. Requirements clarification. What is the agent supposed to do? Who uses it? What is the volume? What is the latency requirement? What is the cost budget?

2. Architecture. Which pattern (ReAct, plan-and-execute, supervisor, swarm)? Why? What are the alternatives, and why did you reject them?

3. Tools. What tools does the agent need? How are they exposed (native, MCP)? What are the schemas? What is the error handling?

4. State and persistence. What state does the agent carry? How is it persisted (MemorySaver, Postgres)? How is long-term memory handled (Store)?

5. Evaluation. How would you evaluate this agent? What is the golden dataset? What evaluators? What is the CI gate?

6. Production. How would you deploy this? What is the cost per request? What is the latency? How would you monitor it? What are the failure modes?

Spend 5 minutes on requirements, 10 on architecture, 5 each on tools/state/eval, 10 on production. 40 minutes total. Leave 5 minutes for the interviewer's questions.

## Worked example 1: Customer support agent

Question: "Design a customer support agent for an e-commerce company."

Requirements (ask the interviewer):

- Volume: 10,000 messages per day.
- Latency: under 5 seconds for the first response.
- Cost: under $0.05 per message.
- Intents: order status, refunds, returns, product questions, bug reports.
- Escalation: 30% of messages require human escalation.

Architecture: Supervisor with 4 specialists (order, refund, return, KB). The supervisor classifies the intent and routes to the right specialist. After the specialist responds, the supervisor decides whether to escalate or resolve.

Why supervisor and not a single agent: the intents are distinct enough that a single agent with 10+ tools would have poor selection accuracy. The supervisor pattern keeps each specialist's tool list small.

Why not swarm: the routing structure is clear (classify, then route). Swarm is for peer-to-peer handoffs, which this problem does not need.

Tools: each specialist has 2-3 tools, exposed as MCP servers. Order specialist: get_order_status, get_tracking_info. Refund specialist: issue_refund (with HITL for over $50). Return specialist: initiate_return. KB specialist: search_docs.

State: conversation messages, current intent, current specialist. Persisted in Postgres (for cross-session continuity). Long-term memory (user preferences, past orders) in the Store.

Evaluation: golden dataset of 100 messages with labeled intents. Evaluators: routing accuracy (95%+), resolution rate (70%+), tool-call correctness (95%+). CI-gated on every prompt change.

Production: Docker deployment with Postgres checkpointer. LangSmith for tracing. Cost: ~$0.03 per message (model routing: cheap model for classification, expensive for response). Latency: ~3 seconds p95 (parallel where possible). Failure modes: tool API outage (fall back to KB), LLM outage (queue and retry), routing error (fall back to generalist).

## Worked example 2: Research agent

Question: "Design a research agent that answers questions with citations."

Requirements: 1000 questions per day, under 60 seconds per answer, under $0.10 per answer, citations required.

Architecture: ReAct with web_search and fetch tools. The agent searches, reads, decides whether to search again, and synthesizes. A separate citation-checker LLM verifies every claim is grounded in a fetched source.

Why ReAct and not plan-and-execute: most research questions need 2-3 searches. Plan-and-execute is overkill for that. ReAct with a 5-call limit is sufficient.

Tools: web_search (Tavily MCP), fetch_and_extract (httpx + trafilatura MCP), citation_check (LLM call).

State: question, search queries, fetched sources, draft answer, citation check result. Persisted in Postgres (for resume on failure).

Evaluation: golden dataset of 30 questions. Evaluators: citation correctness (90%+, LLM-as-judge), answer relevance (95%+, LLM-as-judge), hallucination rate (under 5%, human spot-check).

Production: Docker. LangSmith. Cost: ~$0.05 per answer. Latency: ~30 seconds p95. Failure modes: search API outage (fall back to a different search provider), citation check failure (re-search and re-synthesize, max 3 iterations).

## Worked example 3: Multi-agent code review

Question: "Design a multi-agent system for code review."

Requirements: 100 PRs per day, under 10 minutes per review, reviews must cover correctness, style, and security.

Architecture: Supervisor with 3 specialists (correctness, style, security). Each specialist reviews the PR from its angle. The supervisor aggregates the reviews and posts a single comment on the PR.

Why supervisor and not a single agent: the three perspectives are distinct enough that a single agent would miss things. Each specialist has a focused prompt and a focused tool set.

Why not parallel single agents (no supervisor): the supervisor aggregates and deduplicates (if two specialists flag the same line, the supervisor posts one comment, not two).

Tools: read_file (filesystem MCP), run_tests (custom), search_codebase (custom). Each specialist uses a subset.

State: PR diff, per-specialist reviews, aggregated review. Persisted in Postgres (for tracking review history).

Evaluation: golden dataset of 20 PRs with known issues. Evaluators: issue detection rate (per category), false positive rate, review quality (LLM-as-judge).

Production: GitHub Actions integration. LangSmith. Cost: ~$0.20 per review. Latency: ~5 minutes p95. Failure modes: large PR (skip if over 1000 lines), test failure (note in review but do not block).

## Common mistakes

- Jumping to code. The interviewer wants architecture, not implementation.
- Not discussing evaluation. Evaluation is part of the design, not an afterthought.
- Not discussing failure modes. An agent design without failure modes is naive.
- Over-engineering. Multi-agent when single-agent would do.
- Under-engineering. Single-agent when the problem clearly needs multi-agent.
- Not knowing the trade-offs. "I chose supervisor" without saying why not swarm or hierarchical.

## How to practice

- Pick any product you use (Perplexity, Cursor, Klarna's support bot). Design it out loud in 40 minutes. Record yourself. Listen back. Did you cover all six areas?
- Read the [projects](../projects/) in this repo. They are worked examples of agent design.
- Read engineering blogs from companies that ship agents (Anthropic, LangChain, Cursor, Perplexity). Their design choices are the answers to system design questions.

## Further reading

- [AI Engineering Field Guide: System design](https://github.com/alexeygrigorev/ai-engineering-field-guide/blob/main/interview/questions/04-ai-system-design.md)
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
