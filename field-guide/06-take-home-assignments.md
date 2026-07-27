# Take-home assignments

What companies assign, how to approach them, and how to stand out. Based on analysis of 100+ take-home assignments from AI engineer job postings.

## The typical take-home

Most agentic AI engineer take-homes are one of:

1. Build an agent from a spec (3-5 days). "Build a research agent that answers a question with citations. Include an eval suite."
2. Extend an existing agent (2-3 days). "Here is our current customer support agent. Add a new tool for refunds. Run the eval before and after."
3. Build an eval suite for an existing agent (2-3 days). "Here is our agent. Build a golden dataset of 30 rows and an LLM-as-judge evaluator. Report the agent's score."
4. Debug a failing agent (2-3 days). "Here is our agent and a LangSmith trace of a failure. Diagnose the cause, write a fix, run the eval to verify."

The take-home is the most heavily-weighted round. It is where you demonstrate you can do the job, not just talk about it.

## How to approach it

### Day 1: understand the spec

Read the spec three times. Write down questions. Email the recruiter with the questions (this signals engagement). Do not start coding until you understand what is being asked.

The common misunderstanding: the spec says "build an agent" and the candidate builds the agent but not the eval. The eval is always part of the spec, even if it is not explicitly stated. If you are unsure whether the eval is required, it is required.

### Day 2-3: build the agent

Build the minimum viable agent. Use the patterns from this curriculum. Do not over-engineer - a single ReAct agent with one tool is usually enough for the first version. You can add complexity later if the spec requires it.

Write tests as you go. The tests are part of the submission, not an afterthought.

### Day 4: build the eval

This is where most candidates fail. The eval is not optional.

- Golden dataset: 20-30 rows, hand-labeled.
- Evaluator: at least one (rule-based or LLM-as-judge).
- Run the eval against your agent. Report the score.
- The eval runs in one command: `make eval`.

### Day 5: deploy and document

- Deploy the agent. Docker is the minimum; a live URL is better.
- Write the README. It should explain:
  - What the agent does.
  - The architecture (one paragraph).
  - How to run it locally.
  - How to run the eval.
  - The eval results (the score, with a brief analysis).
  - The trade-offs you made (what you would do differently with more time).
- The README is the first thing the reviewer reads. Make it good.

### Day 6: review and submit

- Re-read the spec. Did you miss anything?
- Run the eval one more time. Does it still pass?
- Test the deployment. Does it still work?
- Submit. Include the GitHub link, the live URL, and a one-paragraph summary.

## What stands out (in a good way)

- A live URL. The reviewer can interact with the agent immediately.
- A clear eval report. The reviewer can see the score and the analysis without running anything.
- A thoughtful README. The reviewer understands what you built and why.
- A simple architecture that fits the problem. No over-engineering.
- Tests. The reviewer can verify your code works.
- A discussion of trade-offs. The reviewer sees you can think critically.

## What stands out (in a bad way)

- No eval. Automatic rejection at most companies.
- No README. The reviewer has to read code to understand what you built.
- Over-engineering. A 5-agent supervisor for a single-agent spec.
- No deployment. Local-only signals you cannot ship to production.
- Bugs in the agent. Run it before submitting.
- Buzzword salad. "I used a hierarchical multi-agent system with A2A and MCP." Did you need to? Why?

## Time management

The take-home is timed. Most companies give 3-7 days and expect 8-15 hours of work. Plan your time:

- Spec understanding: 2 hours.
- Agent implementation: 6-8 hours.
- Eval implementation: 3-4 hours.
- Deployment: 2 hours.
- Documentation: 2 hours.
- Buffer: 2 hours for debugging.

If you spend more than 15 hours, you are over-engineering. Ship what you have and write a thoughtful README about what you would do with more time.

## Ethics

- Do not use AI to write the entire take-home. Most companies can tell, and it is a rejection.
- You can use AI for help (debugging, code review, brainstorming). Disclose this in the README.
- Do not submit work you did for a previous company. This is a fireable offense at most companies.
- If the take-home is too similar to your day job, disclose this and ask for an alternative.

## Real take-home examples

Based on the 100+ assignments analyzed:

### Example 1: Research agent (e-commerce company, 5 days)

> Build a research agent that answers questions about a product catalog. The agent should use a web search tool and a catalog search tool. Include a golden dataset of 20 questions with expected answer sources, and an LLM-as-judge evaluator for citation correctness. Deploy the agent to a public URL.

### Example 2: Customer support agent (fintech, 7 days)

> Extend our existing customer support agent (we give you the code) with a refund tool. The tool should require human approval for refunds over $50. Run the existing eval suite before and after your change, and report the diff. Deploy the updated agent.

### Example 3: Eval suite (AI startup, 3 days)

> Build an evaluation suite for our research agent (we give you the agent). The suite should include: a golden dataset of 30 rows sourced from production traffic, an LLM-as-judge evaluator for answer quality, and a trajectory evaluator for tool-call correctness. Run the suite and report the agent's scores.

### Example 4: Debug a failure (enterprise, 3 days)

> Here is our agent and a LangSmith trace of a production failure (the agent refunded the wrong order). Diagnose the root cause, write a fix, run the eval to verify the fix, and write a one-page post-mortem.

## Further reading

- [AI Engineering Field Guide: Take-home assignments](https://github.com/alexeygrigorev/ai-engineering-field-guide/blob/main/interview/questions/06-home-assignments.md)
- [Real take-home assignments on GitHub](https://github.com/alexeygrigorev/ai-engineering-field-guide/tree/main/interview/data/research-exports)
