# Agent marketplaces

Module: 07-multi-agent-and-a2a
Chapter: 06-agent-marketplaces
Status: draft
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Reason about the trajectory of agent marketplaces (composable agents as a service)
- Identify the trust and verification problem (how do you know an agent is safe to call?)
- Reason about pricing models (per-call, per-task, per-outcome)
- Reason about the regulatory implications (who is liable when an agent misbehaves?)

## Prerequisites

- [05 Cross-framework interop](05-cross-framework-interop.md)

## Conceptual foundation

Agent marketplaces are the next layer up from MCP tool registries. Where MCP registries list tools (functions), agent marketplaces list agents (which may use tools). The vision: an organization can browse a marketplace, find an agent that does what they need, deploy it, and pay per use - the same model as SaaS, but for agents.

In 2026, agent marketplaces are emerging but not yet standardized. The patterns:

1. Static catalogs. A website lists agents with their Agent Cards, descriptions, and pricing. Manual to deploy and use, but the simplest starting point.

2. Runtime registries. A service that agents register with (publishing their Agent Card) and clients query (finding agents by capability). The registry handles discovery; the client and agent handle execution directly.

3. Marketplaces with payments. The marketplace handles not just discovery but also billing - the client pays the marketplace, the marketplace pays the agent owner. This adds a trust layer (the marketplace vouches for the agent) and a payment layer (no need for direct billing relationships).

The trust and verification problem is the central challenge. If you call an unknown agent, how do you know it will not:

- Leak your input data (privacy)
- Return wrong results (quality)
- Take harmful actions in your name (safety)
- Cost more than expected (billing)

The emerging answers:

- Reputation. The marketplace tracks agent quality based on user feedback and eval results.
- Sandboxing. Agents run in sandboxes with restricted permissions; their tool calls are logged and auditable.
- Attestation. Agents are signed by their authors; the signature verifies the agent has not been tampered with.
- Eval transparency. Agents publish their eval results so clients can see measured quality.

The pricing models:

- Per-call. The client pays a fixed amount per task. Simple, but does not account for task complexity.
- Per-token. The client pays for the tokens the agent consumes. Transparent, but unpredictable for the client.
- Per-outcome. The client pays only if the agent succeeds. Aligned incentives, but hard to define "success" for open-ended tasks.

The regulatory implications are unresolved in 2026. If an agent you deployed takes an action that violates a regulation (e.g., gives financial advice without a license), who is liable - you, the agent author, or the marketplace? The EU AI Act is beginning to address this, but the case law is years away.

## Worked example

No code in this chapter - the marketplace is an emerging concept. The exercise: pick a domain (customer support, code review, research) and design an agent marketplace for it. What capabilities would agents advertise? How would you verify quality? How would you price?

## Evaluation

No eval. This chapter is forward-looking.

## Production notes

In production (in 2026), agent marketplaces are not yet ready for mission-critical use. The trust problem is unsolved, the pricing models are unproven, and the regulatory landscape is uncertain. The right posture: experiment with marketplaces for low-stakes tasks (research, summarization), but keep high-stakes tasks (refunds, medical advice, legal advice) on agents you control.

Watch this space. By 2027, the trust problem will have an accepted solution (likely a combination of reputation, sandboxing, and attestation), and marketplaces will become viable for a broader range of tasks.

## Common pitfalls

- Treating marketplaces as production-ready in 2026. Why: the demos look good. Fix: wait for the trust problem to be solved; use marketplaces for experiments, not production.
- Assuming free agents are safe. Why: free feels low-risk. Fix: free agents can still leak data or take harmful actions; apply the same scrutiny as paid agents.
- Not tracking spend on marketplace agents. Why: each call is cheap. Fix: track spend; it adds up.

## Further reading

- [A2A protocol](https://google.github.io/A2A/)
- [EU AI Act](https://artificialintelligenceact.eu/)
- [Agent marketplace discussions](https://github.com/a2aproject/a2a/discussions)

## Checklist

- [ ] Explain the trajectory of agent marketplaces
- [ ] Name the trust and verification problem and the four emerging answers
- [ ] Compare the three pricing models
- [ ] Reason about the regulatory implications for a specific domain
