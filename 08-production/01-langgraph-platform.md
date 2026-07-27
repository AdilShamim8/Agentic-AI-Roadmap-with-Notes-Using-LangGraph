# LangGraph Platform

Module: 08-production
Chapter: 01-langgraph-platform
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Deploy an agent to LangGraph Platform
- Use the Assistants API, cron jobs, and Store management
- Choose between LangGraph Platform and self-hosted Docker based on team size and requirements
- Reason about the cost model and when the platform pays for itself

## Prerequisites

- [07 Multi-agent and A2A](../07-multi-agent-and-a2a/)

## Conceptual foundation

LangGraph Platform is LangChain's managed deployment offering. It handles the production concerns that are tedious to build yourself: horizontal scaling, checkpointing, the Assistants API (for managing multiple agent configurations), cron jobs (for scheduled agents), and the Store (for long-term memory). You bring the agent code; the platform runs it.

The platform's components:

1. Deployments. A deployment is a running instance of your agent. You push your code (via the `langgraph` CLI), and the platform runs it with horizontal scaling, load balancing, and health checks.

2. Assistants. An assistant is a configuration of an agent: a specific system prompt, a specific tool set, a specific model. You can have multiple assistants backed by the same deployment (e.g., a "concise" assistant and a "verbose" assistant). This is how you A/B test prompts.

3. Cron jobs. Scheduled agent invocations. Useful for background tasks (nightly summaries, periodic data checks).

4. Store. Managed long-term memory. The platform hosts the Store; your agent uses it via the same API as in dev.

5. Observability. LangSmith integration is built-in. Every request is traced; dashboards are pre-configured.

The decision: LangGraph Platform vs. self-hosted Docker.

Use LangGraph Platform when:

- Your team is small (under 10 engineers) and you want to focus on agent logic, not infrastructure.
- You need the Assistants API, cron, or managed Store and do not want to build them.
- You are OK with the platform's pricing model (usage-based, with a free tier for development).

Use self-hosted Docker when:

- You have strict data residency requirements (the platform runs in the US; EU customers may need self-hosting).
- You have a large team and the platform's pricing becomes more expensive than self-hosting.
- You need custom infrastructure (special hardware, custom networking, integration with internal systems).

The cost model: the platform charges per request and per hour of compute. For low-traffic agents (under 1000 requests per day), the platform is cheaper than self-hosting (you save on engineering time). For high-traffic agents (over 100,000 requests per day), self-hosting is usually cheaper (you save on per-request fees).

## Worked example

Deploying an agent to LangGraph Platform. Full code in [`examples/deploy_demo.py`](../examples/deploy_demo.py) and [`08-production/langgraph.json`](langgraph.json).

```bash
# 1. Install the CLI
pip install langgraph-cli

# 2. Create langgraph.json in your project root
# (see 08-production/langgraph.json for the template)

# 3. Deploy
langgraph deploy --name my-agent

# 4. The CLI returns a URL. Your agent is now live.
# curl https://my-agent.langgraph.app/invoke -d '{"messages":[{"role":"user","content":"hi"}]}'
```

The `langgraph.json`:

```json
{
  "graphs": {
    "agent": "./examples/conversational_agent_demo.py:agent"
  },
  "env": ".env",
  "dependencies": ["./pyproject.toml"]
}
```

## Evaluation

No eval for deployment chapters. The test is: the deployed agent responds correctly to a test request.

## Production notes

In production, the platform's pre-configured observability is the biggest time-saver. You get latency, cost, error rate, and trace dashboards without building them. The platform's horizontal scaling handles traffic spikes without capacity planning. The trade-off is vendor lock-in: your agent code is portable, but the surrounding infrastructure (Assistants, cron, Store) is platform-specific. If you might migrate to self-hosting later, keep your agent code framework-native (do not use platform-specific APIs in the agent itself; use them only in the deployment layer).

## Common pitfalls

- Using the platform for high-traffic agents without doing the cost math. Why: the free tier is generous. Fix: model the cost at your expected traffic; switch to self-hosting if the platform is more expensive.
- Using platform-specific APIs in agent code. Why: it is convenient. Fix: keep agent code framework-native; use platform APIs only in the deployment layer.
- Not setting up alerts. Why: the platform is "managed." Fix: the platform manages infrastructure, not your agent's quality; set up quality alerts in LangSmith.

## Further reading

- [LangGraph Platform](https://langchain-ai.github.io/langgraph/concepts/langgraph_platform/)
- [LangGraph CLI](https://langchain-ai.github.io/langgraph/cloud/reference/cli/)

## Checklist

- [ ] Deploy an agent to LangGraph Platform
- [ ] Configure an Assistant with a specific prompt and tool set
- [ ] Set up a cron job for a scheduled agent invocation
- [ ] Decide between platform and self-hosting based on team size and traffic
