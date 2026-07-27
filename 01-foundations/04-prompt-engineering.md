# Prompt engineering

Module: 01-foundations
Chapter: 04-prompt-engineering
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

By the end of this chapter, you will be able to:

- Structure a system prompt for an agent (role, constraints, tools, output format) that produces reliable behavior across model providers
- Write tool descriptions that produce reliable tool selection (the single most underrated prompt-engineering skill in 2026)
- Version prompts like code, with a changelog and a regression suite
- Diagnose prompt failures by category (wrong tool, wrong arguments, wrong format, wrong tone) and apply the right fix

## Prerequisites

- [01 What is agentic AI](01-what-is-agentic-ai.md)
- [03 LLM fundamentals](03-llm-fundamentals.md)

## Conceptual foundation

Prompt engineering in 2026 is not what it was in 2023. The "write a clever prompt that makes the model do something surprising" era is over. Modern prompt engineering is closer to API design: you are defining a contract between a human intent and a model behavior, and the contract has to be explicit, versioned, and testable. The model is good enough that the prompt does not need to be clever - it needs to be clear.

The single most important prompt in an agent is the system prompt. The system prompt sets the agent's role, its constraints, the tools it has, and the format of its output. A good system prompt is structured: role first, constraints second, tools third, output format fourth. A bad system prompt is a paragraph of prose that buries the constraints in the middle. The structure matters because models weight earlier tokens more heavily (the primacy effect) and because structured prompts are easier to maintain.

The second most important prompt in an agent is the tool description. Tool descriptions are prompts, not documentation. A tool description that reads "Searches the web" will produce worse tool selection than one that reads "Searches the web for current information. Use this when the user asks about events after 2024, when the question requires real-time data, or when the agent's training data may be outdated. Do not use this for math, code execution, or questions about the agent's own capabilities." The description tells the model when to use the tool, when not to, and what the tool returns. Treat tool descriptions as the most important prompts in your agent.

Few-shot examples belong in tool descriptions, not in the system prompt. If a tool is being selected incorrectly, add a few-shot example to the description showing the right and wrong use. This is more effective than adding examples to the system prompt because the examples are co-located with the tool definition.

Prompt versioning is the discipline that separates professional prompt engineering from hobbyist prompt engineering. A prompt is code. It changes over time. Those changes need to be tracked, reviewed, and tested. The minimum bar: prompts live in their own files (not inline in Python), are versioned with a comment header, and have a regression test that runs whenever the prompt changes. The test is an eval suite: a golden dataset, an evaluator, and a pass threshold. When you change the prompt, you run the eval, and you require the new score to be at least as good as the old score.

The four categories of prompt failure:

1. Wrong tool. The agent calls the wrong tool, or calls no tool when it should. Fix: improve the tool description, add a few-shot example of the correct tool selection.

2. Wrong arguments. The agent calls the right tool with wrong arguments. Fix: improve the argument descriptions in the tool schema, add a validation step that retries on schema failure, consider a simpler schema.

3. Wrong format. The agent returns output that does not match the expected format (wrong JSON shape, wrong markdown structure, wrong citation format). Fix: add an explicit output format section to the system prompt, use structured outputs (JSON mode or function calling) instead of free text, add a post-processing step that reformats.

4. Wrong tone or content. The agent returns the right format but the wrong content (too verbose, too terse, factually wrong, off-topic). Fix: add a constraint to the system prompt, add a reflection step where the agent critiques its own output before returning it, add an evaluator that catches the specific failure.

## Worked example

Here is a system prompt structure that works across providers:

```python
SYSTEM_PROMPT = """You are a customer support agent for Acme Corp.

Your role: help customers with order issues, refunds, and product questions.

Your constraints:
- Never promise a refund without checking the order status first.
- Never share internal system information with customers.
- If you are unsure, escalate to a human rather than guessing.
- Keep responses under 150 words.

Your tools:
- get_order_status(order_id): returns the status of an order.
- issue_refund(order_id, amount, reason): issues a refund. Requires human approval for amounts over $50.
- escalate_to_human(reason): escalates the conversation to a human agent.

Your output format:
- Always end your response with one of: [RESOLVED], [ESCALATED], or [AWAITING_INFO].
- If you used a tool, mention what you did in plain language before stating the outcome.
"""
```

And here is a tool description that produces reliable selection:

```python
from langchain_core.tools import tool

@tool
def get_order_status(order_id: str) -> dict:
    """Check the status of a customer's order.

    Use this when:
    - The customer asks where their order is
    - The customer mentions a delayed, missing, or damaged order
    - You need to verify an order exists before processing a refund

    Do NOT use this when:
    - The customer is asking a general product question (use search_docs instead)
    - The customer wants to cancel an order (use cancel_order instead)

    Args:
        order_id: The order identifier, format 'ACME-XXXXXX'. If the customer
                  gives a different format, ask them to clarify before calling.

    Returns:
        A dict with keys: status (str), shipped_date (str|None),
        tracking_number (str|None), items (list).
    """
    # implementation omitted
```

## Evaluation

There is no eval for this chapter's prompt snippets because they are illustrative. In your own agents, every prompt change should be gated by an eval. The minimum eval for a prompt change:

- A golden dataset of at least 20 inputs
- An evaluator (LLM-as-judge or rule-based) that measures the behavior the prompt is supposed to control
- A pass threshold (e.g., "tool selection accuracy >= 90 percent")
- A CI step that runs the eval on every PR that touches the prompt

See [06 Evals and observability](../06-evals-and-observability/) for the full treatment.

## Production notes

In production, prompts change more often than code. New failure modes appear, stakeholders request tone changes, model updates shift behavior. The prompt-as-code discipline is what keeps this manageable. The patterns that work:

- Prompts live in `.py` files (or `.txt` files loaded at runtime), not inline in business logic. This makes them diffable and reviewable.
- Every prompt has a comment header with the last-reviewed date and the eval score it was last validated against.
- Prompt changes are PRs, with the eval diff posted as a PR comment by CI.
- A prompt library (a directory of reusable prompt fragments) keeps common patterns (output formats, citation styles, safety constraints) consistent across agents.

The most common production failure: a model provider ships an update, the model's behavior shifts slightly, and an agent that was working starts failing in subtle ways. The defense is the eval suite - it catches the regression before users do. Without an eval suite, you find out from customer complaints, which is too late.

## Common pitfalls

- Writing clever prompts instead of clear prompts. Why: the "prompt engineering" discourse rewards cleverness. Fix: write the most boring, explicit prompt that works.
- Putting tool descriptions in the system prompt. Why: it feels organized. Fix: descriptions belong in the tool definition, where the model can co-locate them with the schema.
- Not versioning prompts. Why: prompts feel like configuration, not code. Fix: treat them as code, with PRs and evals.
- Adding examples to the system prompt instead of to tool descriptions. Why: examples feel global. Fix: co-locate examples with the tool they illustrate.

## Further reading

- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) - the Anthropic essay that influenced the system-prompt structure above
- [Prompt Engineering Guide](https://www.promptingguide.ai/) - open-source reference for prompt patterns
- [OpenAI prompt engineering best practices](https://platform.openai.com/docs/guides/prompt-engineering) - provider-specific guidance

## Checklist

You understand this chapter if you can:

- [ ] Structure a system prompt with role, constraints, tools, and output format
- [ ] Write a tool description that specifies when to use, when not to use, and what it returns
- [ ] Set up a prompt-as-code workflow with versioning and eval gating
- [ ] Diagnose a prompt failure as wrong-tool, wrong-arguments, wrong-format, or wrong-content, and apply the right fix
