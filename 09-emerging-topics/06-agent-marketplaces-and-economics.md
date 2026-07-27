# Agent marketplaces and economics

Module: 09-emerging-topics
Chapter: 06-agent-marketplaces-and-economics
Status: draft
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Reason about the economics of agent marketplaces (supply, demand, pricing, trust)
- Identify the open problems (verification, liability, reputation)
- Reason about the trajectory (when marketplaces become viable for production)

## Prerequisites

- [06 Agent marketplaces](../07-multi-agent-and-a2a/06-agent-marketplaces.md)

## Conceptual foundation

Agent marketplaces (covered in module 07 from a technical perspective) have an economic dimension that determines whether they succeed or fail. This chapter covers the economics.

The supply side: who builds agents for marketplaces, and why? In 2026, the supply is mostly internal (companies build agents for their own use) and open-source (developers publish agents for free). A commercial supply (agents built for sale) is emerging but small. The supply will grow as the trust problem is solved - developers will not invest in building agents for sale if buyers cannot verify quality.

The demand side: who buys agents, and for what? In 2026, the demand is mostly from companies that want to add an AI capability (customer support, code review) without building it themselves. The demand is constrained by the same trust problem - buyers will not deploy agents they cannot verify.

The pricing models:

1. Per-call. The buyer pays a fixed amount per task. Simple, but does not account for task complexity. Suitable for narrow, well-defined tasks.

2. Per-token. The buyer pays for the tokens the agent consumes. Transparent, but unpredictable for the buyer. Suitable for buyers who want to see exactly what they are paying for.

3. Per-outcome. The buyer pays only if the agent succeeds. Aligned incentives, but hard to define "success" for open-ended tasks. Suitable for tasks with a clear success criterion (refund issued, ticket resolved, code merged).

4. Subscription. The buyer pays a monthly fee for unlimited use. Predictable, but misaligns incentives (the agent author is not incentivized to improve quality once the subscription is sold). Suitable for high-volume, low-stakes tasks.

The trust problem is the central economic challenge. Without trust, the market cannot clear: buyers will not buy, sellers will not invest. The emerging solutions (reputation, sandboxing, attestation, eval transparency) are covered in module 07. The economic question is which solution wins - and that is unresolved in 2026.

The liability problem is the legal dimension. If an agent from a marketplace causes harm (gives bad medical advice, discriminates in hiring, violates privacy), who is liable? The buyer, the seller, or the marketplace? The EU AI Act is beginning to address this, but the case law is years away. Until it is settled, marketplaces will be limited to low-stakes tasks.

## Worked example

No code. The exercise: pick a domain (customer support, code review, legal research). Design a marketplace for it. What is the supply (who builds agents)? What is the demand (who buys)? What is the pricing model? How is trust established?

## Evaluation

No eval. This chapter tracks the frontier.

## Production notes

In production (in 2026), do not rely on agent marketplaces for mission-critical tasks. Use them for experiments and for low-stakes tasks (research, summarization). The trust and liability problems will be solved over the next 2-3 years; until then, build or buy agents that you control.

## Further reading

- [A2A protocol](https://google.github.io/A2A/)
- [EU AI Act](https://artificialintelligenceact.eu/)
- [The economics of AI agents](https://a16z.com/the-economic-case-for-agentic-ai/)

## Checklist

- [ ] Reason about the supply and demand sides of an agent marketplace
- [ ] Compare the four pricing models
- [ ] Identify the trust and liability problems and their emerging solutions
- [ ] Reason about when marketplaces become viable for production
