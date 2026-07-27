# Interview prep

How to prepare for agentic AI engineer interviews. Based on analysis of interview reports and practitioner experience.

## The typical interview process

Most agentic AI engineer interviews have 4-5 rounds:

1. Recruiter screen (30 minutes). Background, salary expectations, timeline.
2. Hiring manager (45 minutes). Your experience, the role, fit.
3. Technical screen (60 minutes). Coding or system design, often both.
4. Take-home assignment (3-7 days). Build a small agent or extend an existing one.
5. Onsite (3-4 hours). System design, coding, behavioral, sometimes a deep-dive on the take-home.

The process takes 3-6 weeks from first contact to offer.

## System design for agents

The system design round is the most distinctive part of an agentic AI engineer interview. The questions are agent-specific:

- "Design a customer support agent for an e-commerce company."
- "Design a research agent that summarizes academic papers."
- "Design a multi-agent system for code review."
- "Design an agent that can answer questions about a company's internal documents."

The expected answer covers:

1. Architecture. Which pattern (ReAct, plan-and-execute, supervisor)? Why? What are the alternatives, and why did you reject them?
2. Tools. What tools does the agent need? How are they exposed (native, MCP)? What are the schemas?
3. State and persistence. What state does the agent carry? How is it persisted (MemorySaver, Postgres)? How is long-term memory handled (Store)?
4. Evaluation. How would you evaluate this agent? What is the golden dataset? What evaluators?
5. Production. How would you deploy this? What is the cost per request? What is the latency? How would you monitor it?
6. Failure modes. What can go wrong? How would you detect it? How would you fix it?

The common mistakes:

- Jumping to code without discussing the architecture. The interviewer wants to see your thinking, not your typing.
- Not discussing evaluation. An agent design without an eval plan is incomplete.
- Not discussing failure modes. An agent design without failure-mode analysis is naive.
- Over-engineering. Multi-agent with 5 specialists when a single ReAct agent would do.

## Coding rounds

The coding round is usually one of:

1. Implement a LangGraph agent from a spec. "Build a ReAct agent with a calculator tool and a web search tool. Include a max-iteration limit and error handling."
2. Implement a tool. "Build a tool that queries a SQLite database. Include schema validation and error handling."
3. Implement an evaluator. "Build an LLM-as-judge evaluator for answer quality. Include a rubric and a structured output schema."

The expectations:

- Working code, not pseudocode.
- Type hints, docstrings, error handling.
- Tests (at least one test for the happy path).
- The code follows the patterns in this curriculum (StateGraph, ToolNode, Pydantic schemas).

## Take-home assignments

The take-home is the most important round. It is where you demonstrate you can build a real agent, not just talk about it.

Typical take-homes:

- "Build a research agent that answers a question with citations. Include an eval suite with 20 rows and an LLM-as-judge evaluator."
- "Extend this existing agent (we give you the code) with a new tool. Run the eval before and after, and report the diff."
- "Build a multi-agent system for a specific domain. Document the architecture, the eval, and the production deployment plan."

The bar:

- The agent works. It does what the spec says.
- The eval suite exists. It has at least 20 rows. It has at least one evaluator. It runs.
- The code is clean. Type hints, docstrings, tests, no dead code.
- The README explains the architecture, the eval results, and the trade-offs.
- The code is deployed (or deployable). A live URL is worth 10x a local-only submission.

The common mistakes:

- Shipping the agent without an eval. This is an automatic rejection at most companies.
- Over-engineering. A 5-agent supervisor when the spec asked for a single agent.
- Not deploying. A local-only submission signals you cannot ship to production.
- Not writing a README. The reviewer should not have to read your code to understand what you built.

## Behavioral rounds

The behavioral round assesses:

- Collaboration. Tell me about a time you worked with a product manager to define an agent's behavior.
- Ambiguity. Tell me about a time the spec was unclear and you had to make a decision.
- Failure. Tell me about a time an agent you built failed in production. What did you do?
- Learning. Tell me about a time you had to learn a new pattern quickly. (This is common in agentic AI, where the field evolves fast.)

Use the STAR format: Situation, Task, Action, Result. Be specific. Name the agent, the failure, the fix.

## How to prepare

1. Build the projects in [projects/](../projects/). At least 2-3 of them. Deploy them. Have live URLs.
2. Write eval suites for every agent you build. This is the skill most candidates lack.
3. Practice system design out loud. Talk through an agent design with a friend or a rubber duck.
4. Read the [curriculum](../01-foundations/) end-to-end. You should be able to discuss any chapter.
5. Read the [awesome list](../awesome.md). Know the key papers and tools.
6. Have a portfolio site (or a GitHub profile) that shows your agents, with evals and live demos.

## What interviewers look for

Based on conversations with hiring managers:

- Can you build a working agent? (Demonstrated by the take-home.)
- Can you evaluate it? (Demonstrated by the eval suite in the take-home.)
- Can you reason about architecture? (Demonstrated by the system design round.)
- Can you write production code? (Demonstrated by the coding round and the take-home.)
- Can you communicate? (Demonstrated by every round.)
- Are you humble about the LLM's limitations? (Demonstrated by how you talk about failure modes.)

The candidates who get offers are the ones who can do all six. The candidates who do not get offers usually fail on "can you evaluate it" - they ship agents without evals and hope the interviewer does not notice.

## Red flags for interviewers

- Claiming the agent "works perfectly." It does not. Talk about failure modes.
- Not mentioning evaluation until asked. Evaluation should be in your system design without prompting.
- Over-using buzzwords (MCP, A2A, multi-agent) without explaining when to use them.
- Not being able to read a LangSmith trace. This is a core debugging skill.
- Treating prompts as configuration, not code. Prompts are versioned, reviewed, tested.

## Further reading

- [AI Engineering Field Guide: Interview prep](https://github.com/alexeygrigorev/ai-engineering-field-guide/blob/main/interview/01-interview-process.md)
- [Take-home assignments from real companies](https://github.com/alexeygrigorev/ai-engineering-field-guide/blob/main/interview/data/research-exports/home-assignments.md)
