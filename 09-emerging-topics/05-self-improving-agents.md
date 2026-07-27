# Self-improving agents

Module: 09-emerging-topics
Chapter: 05-self-improving-agents
Status: draft
Last reviewed: 2026-07-27
Estimated time: 1 hour

## Learning objectives

- Distinguish self-improving agents (agents that get better over time without code changes) from agents that learn within a single task (reflexion)
- Identify the mechanisms (prompt refinement, tool refinement, memory consolidation)
- Reason about the safety implications (a self-improving agent can drift in unexpected directions)
- Reason about the current state and trajectory

## Prerequisites

- [03 Reflexion](../05-agentic-patterns/03-reflexion.md)

## Conceptual foundation

A self-improving agent is an agent that updates its own behavior based on experience, without a human shipping a code change. This is distinct from reflexion (which improves within a single task) and from fine-tuning (which requires a training step). Self-improving agents modify their prompts, their tool descriptions, or their memories based on what worked and what did not.

The mechanisms:

1. Prompt refinement. The agent's system prompt is updated based on production feedback. The agent identifies patterns in failures ("I keep forgetting to ask for the order ID before calling issue_refund") and adds an instruction to its prompt ("Always ask for the order ID before calling issue_refund"). The refinement can be automated (an LLM reviews the failure log and proposes prompt changes) or human-in-the-loop (the LLM proposes, a human approves).

2. Tool refinement. The agent's tool descriptions are updated based on tool-selection failures. The agent identifies patterns ("I keep calling search when I should call calculator") and updates the tool descriptions to be clearer. This is the same as prompt refinement but applied to tools.

3. Memory consolidation. The agent's long-term memory is consolidated and pruned based on usage. Memories that are retrieved often are strengthened; memories that are never retrieved are forgotten. This is the analogue of sleep consolidation in human memory.

The safety implications are significant. A self-improving agent can drift in unexpected directions: the prompt refinement that fixes one failure might introduce another; the memory consolidation that improves efficiency might forget something important. The defenses: every self-improvement is gated by the eval suite (if the eval score drops, the improvement is reverted), every self-improvement is logged (so you can audit what changed and when), and every self-improvement is reviewed by a human (at least weekly, for production agents).

The current state (2026): self-improving agents are emerging. Prompt refinement and tool refinement are production-ready in narrow cases (the LLM proposes, a human approves). Memory consolidation is research-grade. Fully autonomous self-improvement (no human in the loop) is not yet safe for production.

## Worked example

No code - this chapter is forward-looking. The exercise: pick an agent you have built. What is one prompt refinement that would improve it? How would you discover that refinement automatically from production data?

## Evaluation

No eval. The eval for a self-improving agent is the same as for any agent, plus a meta-eval: does the agent's eval score improve over time without code changes?

## Production notes

In production (in 2026), use self-improvement in human-in-the-loop mode. The agent proposes improvements (prompt changes, tool description changes, memory updates); a human reviews and approves. The improvements are gated by the eval suite. This is the safe path to self-improvement. Fully autonomous self-improvement is not yet safe; do not deploy it in production.

## Further reading

- [Reflexion paper](https://arxiv.org/abs/2303.11366)
- [Voyager: Open-Ended Embodied Agent](https://arxiv.org/abs/2305.16291) - self-improving agent in Minecraft
- [Self-Refine](https://arxiv.org/abs/2303.17651)

## Checklist

- [ ] Distinguish self-improving agents from reflexion and fine-tuning
- [ ] Name the three self-improvement mechanisms
- [ ] Reason about the safety implications of autonomous self-improvement
- [ ] Design a human-in-the-loop self-improvement workflow
