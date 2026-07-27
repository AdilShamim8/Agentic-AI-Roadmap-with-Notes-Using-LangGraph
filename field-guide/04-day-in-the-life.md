# A day in the life

Based on practitioner reports and the author's experience. This is what the work actually looks like.

## Morning: standup and triage (9:00 - 10:00)

- Standup with the team. What did you do yesterday, what are you doing today, what is blocking you. For agentic AI engineers, "what I did yesterday" is usually one of: shipped a prompt change (with eval diff), debugged a production failure (using LangSmith traces), built a new tool (MCP server), or wrote a new eval.

- Triage the overnight alerts. Did the agent fail overnight? Did the cost per request spike? Did the eval suite flag a regression? The dashboard tells you; you spend 15 minutes deciding what to investigate first.

## Late morning: development (10:00 - 12:00)

- Heads-down development. This is the core of the work. You are either:

  - Building a new agent or extending an existing one. You write Python (LangGraph), you iterate on the prompt, you add tools (MCP servers), you wire up the checkpointer. You test locally with LangGraph Studio.

  - Building an eval suite. You sample production traffic, label rows, write evaluators (rule-based, LLM-as-judge, trajectory). You run the eval against the current agent and against the proposed change, and you compare.

  - Debugging a production failure. You open LangSmith, find the failing trace, walk through the nodes, identify where the agent went wrong. You write a fix, run the eval, ship the fix.

  - Reviewing a PR. Your teammate shipped a prompt change. You review the eval diff (did the change improve the score or regress it?), you check the code, you approve or request changes.

## Lunch (12:00 - 13:00)

- Eat. Talk to humans. Do not look at the dashboard.

## Afternoon: more development, meetings (13:00 - 17:00)

- More heads-down development. The afternoon block is for the hard work - the morning was for the easy work.

- One or two meetings. With product (what should the agent do next?), with the ML team (which model should we use?), with the backend team (how do we deploy this?), with stakeholders (demo the agent, get feedback).

- Code review. You review PRs from teammates. The review focuses on: technical accuracy (does the agent do what the PR says?), eval results (did the eval score improve?), and prompt quality (is the new prompt clear?).

## End of day: ship and wrap up (17:00 - 18:00)

- Ship what you built. Open the PR, wait for CI (which runs the eval suite), merge if the eval passes.

- Update the agent's "Last reviewed" date. Write a one-paragraph changelog entry for what you shipped.

- Check the dashboard one more time. Is the agent healthy? If yes, go home. If no, decide whether it can wait until tomorrow or needs attention tonight.

## What the work feels like

The work is satisfying because you can see it work. You build an agent, you run it, it does something useful. The eval suite tells you whether it is good. The production dashboard tells you whether users find it useful. The feedback loop is tight.

The work is frustrating because the LLM is probabilistic. The agent that worked yesterday fails today because the model was updated, or because the user asked a slightly different question, or because the tool API changed. Debugging probabilistic systems is a different skill from debugging deterministic systems, and it takes time to learn.

The work is interdisciplinary. You talk to product managers (what should the agent do?), ML engineers (which model should we use?), backend engineers (how do we deploy this?), designers (how do we show tool calls in the UI?), lawyers (is the agent compliant?), and users (does this actually help?). The agentic AI engineer is the connective tissue between these groups.

## What you do not do

- You do not train models. The model is a black box; you call its API.
- You do not write much HTML/CSS/JavaScript. The frontend is a separate team (unless you are at a small startup).
- You do not manage infrastructure. The platform team handles Kubernetes, databases, networking.
- You do not do data engineering. The data team handles pipelines.
- You do not do user research. The product team handles that.

You focus on the agent: the prompt, the tools, the orchestration, the evaluation. Everything else is someone else's job (in a larger org) or your job too (in a small startup).

## The cadence

- Weekly: ship at least one change (prompt, tool, eval improvement) per week.
- Monthly: review the eval suite, add rows from production failures, retire stale rows.
- Quarterly: review the agent architecture. Is the pattern still right? Should we upgrade from ReAct to plan-and-execute? Should we split into a multi-agent system?
- Ongoing: monitor the dashboard, respond to alerts, learn the new patterns as the field evolves.

## The hardest part

The hardest part is not the code. The code is straightforward - LangGraph is a clean framework, Python is a familiar language. The hardest part is the judgment:

- When is an agent the right abstraction, and when is a chain or a workflow better?
- When do you upgrade from ReAct to plan-and-execute?
- When do you split a single agent into a multi-agent system?
- When do you add a new tool, and when do you improve an existing tool's description?
- When is the eval suite trustworthy, and when is it misleading?
- When do you ship a change that improves the eval score but feels wrong?

These judgments come from experience. The curriculum gives you the patterns; the field guide tells you what the work looks like; the projects give you practice. The judgment comes from doing the work.
