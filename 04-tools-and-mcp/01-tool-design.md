# Tool design

Module: 04-tools-and-mcp
Chapter: 01-tool-design
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Design tool schemas that produce reliable tool selection and argument correctness
- Write tool descriptions that specify when to use, when not to use, and what the tool returns
- Design tool error returns that let the LLM recover gracefully
- Diagnose the four tool-design failure modes (vague description, ambiguous schema, silent failure, over-broad tool)

## Prerequisites

- [01 Conversational agents](../03-agents-in-practice/01-conversational-agents.md)

## Conceptual foundation

Tool design is the most underrated skill in agent engineering. The model is only as good as the tools it can call, and a badly designed tool will produce failures no matter how good the model is. The mistake most engineers make is treating tools as functions - documenting what they do and how to call them. Tools are not functions; they are prompts. The tool description is a prompt that tells the LLM when to use the tool. The tool schema is a prompt that tells the LLM how to call it. Both must be designed with the same care as a system prompt.

The four components of a well-designed tool:

1. Name. A verb-noun pair that says what the tool does: `get_order_status`, `issue_refund`, `search_web`. Avoid generic names like `query` or `fetch` - the LLM has to guess what is being queried.

2. Description. Three sections: when to use, when not to use, what it returns. The "when not to use" section is the most important and the most often omitted. Without it, the LLM over-selects the tool.

3. Schema. Each argument has a type, a description, and (where relevant) a constraint. The description is a prompt - "The order ID, format 'ACME-XXXXXX'" is better than "The order ID". Constraints (regex patterns, enums, ranges) reduce argument hallucination.

4. Error return. Tools should not raise exceptions; they should return error messages that the LLM can act on. "Order ABC123 not found. Check the order ID and try again." is actionable. A raised exception crashes the graph.

The four tool-design failure modes:

1. Vague description. "Searches the web." The LLM calls it for everything. Fix: specify when to use, when not to use, and what it returns.

2. Ambiguous schema. A `query` argument with no description. The LLM guesses what to pass. Fix: describe each argument with enough detail that the LLM can infer the right value from the conversation.

3. Silent failure. The tool returns an empty string or `None` on error. The LLM does not know it failed and proceeds as if it succeeded. Fix: return explicit error messages.

4. Over-broad tool. One tool that does ten things (`manage_orders` that creates, reads, updates, and deletes). The LLM cannot reliably select the right sub-action. Fix: split into `get_order`, `create_order`, `update_order`, `delete_order`.

## Worked example

A poorly designed tool and a well-designed version of the same tool, side by side. Full code in [`examples/tool_design_demo.py`](../examples/tool_design_demo.py).

Poor:

```python
@tool
def query(data: str) -> str:
    """Queries the system."""
    return db.query(data)  # What data? What system? What does it return?
```

Well-designed:

```python
@tool
def get_order_status(order_id: str) -> str:
    """Check the current status of a customer's order.

    Use this when:
    - The customer asks where their order is
    - The customer mentions a delayed, missing, or damaged order
    - You need to verify an order exists before processing a refund or return

    Do NOT use this when:
    - The customer is asking a general product question (use search_docs instead)
    - The customer wants to cancel an order (use cancel_order instead)
    - The customer wants to track a shipment (use get_tracking_info instead)

    Args:
        order_id: The order identifier, format 'ACME-XXXXXX' (e.g., 'ACME-123456').
                  If the customer gives a different format, ask them to clarify
                  before calling this tool.

    Returns:
        A string like 'Order ACME-123456: shipped on 2026-07-20, tracking 1Z999...',
        or 'Order ACME-123456 not found' if the ID does not exist.
    """
    order = db.get_order(order_id)
    if not order:
        return f"Order {order_id} not found. Check the order ID and try again."
    return f"Order {order_id}: {order.status} on {order.shipped_date}, tracking {order.tracking_number}"
```

## Evaluation

A golden dataset of 20 user messages, each labeled with the expected tool call (or "none"). The evaluator checks tool-selection accuracy and argument correctness. Run the eval on both the poor and the well-designed tool; the difference is typically 30+ percentage points.

## Production notes

In production, tool design is the single highest-leverage improvement you can make. A 10 percent improvement in tool-selection accuracy compounds across every agent call. The process: collect production traces, identify the top tool-selection failures, improve the relevant tool descriptions, re-run the eval, ship. This is a weekly cadence for a mature agent team.

## Common pitfalls

- Treating tools as functions. Why: it is the familiar mental model. Fix: treat tools as prompts; the description and schema are both prompts.
- Omitting the "when not to use" section. Why: it feels redundant. Fix: it is the most important section for selection accuracy.
- Raising exceptions from tools. Why: it is the Python idiom. Fix: return error messages so the LLM can recover.
- Building over-broad tools. Why: fewer tools feels simpler. Fix: split; the LLM selects better with more specific tools.

## Further reading

- [Anthropic: tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [OpenAI: function calling best practices](https://platform.openai.com/docs/guides/function-calling)
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)

## Checklist

- [ ] Design a tool with name, description (when to use / not use / returns), schema, and error return
- [ ] Write the "when not to use" section for every tool
- [ ] Return error messages instead of raising exceptions
- [ ] Measure tool-selection accuracy on a golden dataset before and after a description change
