# Structured outputs and tool calling

Module: 01-foundations
Chapter: 05-structured-outputs-and-tools
Status: stable
Last reviewed: 2026-07-27
Estimated time: 3 hours

## Learning objectives

By the end of this chapter, you will be able to:

- Get reliable structured output from an LLM using JSON mode, function calling, and Pydantic schemas
- Build a tool-calling loop with proper retry on validation failure
- Choose between JSON mode and function calling for a given task
- Diagnose and fix the four common structured-output failure modes

## Prerequisites

- [03 LLM fundamentals](03-llm-fundamentals.md)
- [04 Prompt engineering](04-prompt-engineering.md)

## Conceptual foundation

Structured outputs are the bridge between LLMs and software. An LLM that returns free text is a chatbot. An LLM that returns a validated JSON object matching a schema is a function you can compose into a system. Every agent, every RAG pipeline, every LLM-powered feature in production depends on structured outputs. This chapter is the foundation of everything you will build in modules 02 through 09.

There are three mechanisms for getting structured output from a modern LLM, in order of reliability:

1. Function calling (also called tool calling). You define a function schema (name, description, parameters as a JSON Schema). The model is trained to either call the function with arguments that match the schema or not call it. The model returns a structured tool-call object, not free text. This is the most reliable mechanism because the model is fine-tuned to produce schema-valid output, and the API validates the output against the schema before returning it. As of 2026, OpenAI, Anthropic, and Gemini all support function calling with strict schema enforcement.

2. JSON mode. You tell the model to return valid JSON, and the API guarantees the output is parseable as JSON. JSON mode does not enforce a schema - it only guarantees the output is valid JSON. You still need to validate the JSON against your schema yourself. JSON mode is less reliable than function calling for complex schemas but more reliable than free-text prompts. Use it when function calling is not available or when you want a single JSON object rather than a tool call.

3. Prompt-based structuring. You describe the desired format in the prompt and parse the model's free-text response. This is the least reliable mechanism and should only be used when the first two are not available. It is the fallback for open models that do not support function calling.

The decision rule: use function calling when you need the model to decide whether to call a tool and with what arguments. Use JSON mode when you always want a structured response (not a tool call) and the model supports JSON mode. Use prompt-based structuring only as a last resort.

Pydantic is the schema language of choice for Python LLM engineering. LangChain, LangGraph, OpenAI's SDK, and Anthropic's SDK all accept Pydantic models as schemas. A Pydantic model defines the fields, their types, and their descriptions. The descriptions are prompts - they tell the model what to put in each field. Treat field descriptions as seriously as you treat tool descriptions.

The tool-calling loop is the heart of every agent. In its simplest form:

1. Send the user's message and the tool definitions to the model.
2. The model either responds with text (done) or with a tool call (continue).
3. If the model called a tool, execute the tool, append the result to the conversation, and go to step 1.
4. Repeat until the model responds with text or a max-iteration limit is hit.

The max-iteration limit is not optional. Without it, a confused model can loop forever, calling the same tool with the same arguments indefinitely. In production, set a max-iteration limit (5 to 10 for most agents), log when it is hit, and alert on the rate.

Retry on validation failure is the second essential. When the model returns a tool call with invalid arguments (wrong type, missing field, out-of-range value), you have three options: retry the request with an error message telling the model what was wrong, fall back to a simpler behavior, or fail the request. Retrying is usually correct, but cap it at 1 to 2 retries - if the model cannot get it right in three tries, more retries will not help.

The four common structured-output failure modes:

1. Schema violation. The model returns arguments that do not match the schema (wrong type, missing required field, extra field). Fix: simplify the schema, improve field descriptions, add a retry with feedback.

2. Hallucinated tool. The model calls a tool that does not exist, or invents arguments that are not in the schema. Fix: ensure the model supports strict function calling (OpenAI's `strict=True`, Anthropic's tool use), reduce the model's temperature, ensure the tool list is not too long (more than 10 tools degrades selection quality).

3. Wrong tool. The model calls a real tool but the wrong one. Fix: improve tool descriptions, especially the "do not use when" sections.

4. Argument hallucination. The model calls the right tool with arguments that are not grounded in the conversation (e.g., invents an order ID instead of asking the user). Fix: add an explicit instruction to the tool description ("If the user has not provided an order_id, ask for it before calling this tool"), add a validation step that checks arguments against the conversation.

## Worked example

Here is a complete, runnable tool-calling loop with Pydantic schemas, retry on validation failure, and a max-iteration limit. The full code is in [`examples/structured_output_demo.py`](../examples/structured_output_demo.py).

```python
from typing import Annotated
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

class WeatherArgs(BaseModel):
    location: str = Field(description="City and state, e.g., 'San Francisco, CA'")
    units: str = Field(description="'fahrenheit' or 'celsius'. Default to fahrenheit.")

@tool(args_schema=WeatherArgs)
def get_weather(location: str, units: str = "fahrenheit") -> str:
    """Get the current weather for a location.

    Use this when the user asks about current weather, temperature,
    or conditions. Do not use this for forecasts (use get_forecast instead).

    Returns a string like '72F, sunny'.
    """
    # In production, call a real weather API here.
    return f"72{units[0].upper()}, sunny"

llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools([get_weather])

def run_agent(user_message: str, max_iterations: int = 5) -> str:
    messages = [HumanMessage(content=user_message)]
    for i in range(max_iterations):
        response = llm.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            return response.content
        for call in response.tool_calls:
            try:
                result = get_weather.invoke(call["args"])
                messages.append(AIMessage(content=result, tool_call_id=call["id"]))
            except Exception as e:
                messages.append(AIMessage(
                    content=f"Tool call failed: {e}. Please try with different arguments.",
                    tool_call_id=call["id"],
                ))
    return "I was unable to complete your request. Please try again."

print(run_agent("What's the weather in San Francisco?"))
```

## Evaluation

The eval for this pattern measures two things: tool-selection accuracy (did the agent call the right tool?) and argument correctness (did the agent pass the right arguments?). A minimal golden dataset:

```csv
input,expected_tool,expected_args
"What's the weather in SF?",get_weather,"{""location"": ""San Francisco, CA""}"
"What's 2+2?",none,
"What's the weather in Celsius in Tokyo?",get_weather,"{""location"": ""Tokyo"", ""units"": ""celsius""}"
```

The evaluator checks that the called tool matches `expected_tool` and that the called arguments match `expected_args` (with fuzzy matching for optional fields). Run this eval on every change to the tool description or the system prompt. See [06 Evals and observability](../06-evals-and-observability/) for the full eval pipeline.

## Production notes

In production, structured outputs fail more than you expect. The model is good but not perfect, and the failure rate compounds across a multi-step agent. A 95 percent per-call success rate means a 5-step agent succeeds only 77 percent of the time without retries. The defenses:

- Always validate tool arguments against the schema before executing the tool. Pydantic does this for you if you use `args_schema`.
- Always retry on validation failure, with a cap of 1 to 2 retries. Include the validation error in the retry so the model can correct itself.
- Always log tool calls and their arguments, with the conversation ID and the trace ID. This is how you diagnose failures in production.
- Always set a max-iteration limit. The default in LangGraph's `create_react_agent` is 25; for most production agents, 5 to 10 is more appropriate.

The most common production failure: a model update silently changes tool-calling behavior. The model that was 98 percent accurate on tool selection drops to 92 percent after an update, and your agent starts failing in ways that are hard to reproduce. The defense is the eval suite, run on every model version, with a rollback plan if the score drops below threshold.

## Common pitfalls

- Not setting a max-iteration limit. Why: it works fine in dev. Fix: set it, always, even for "simple" agents.
- Not retrying on validation failure. Why: it feels like the model should get it right. Fix: retry once with the error message; it fixes most failures.
- Not validating arguments before executing the tool. Why: the model "usually" gets it right. Fix: always validate; Pydantic makes this a one-liner.
- Putting too many tools in the agent. Why: more tools feels more capable. Fix: more than 10 tools degrades selection quality; use a router agent or dynamic tool loading instead.

## Further reading

- [OpenAI function calling guide](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic tool use guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Pydantic documentation](https://docs.pydantic.dev/)
- [LangChain tools documentation](https://python.langchain.com/docs/concepts/tools/)

## Checklist

You understand this chapter if you can:

- [ ] Get a validated JSON object from an LLM using both function calling and JSON mode
- [ ] Build a tool-calling loop with retry on validation failure and a max-iteration limit
- [ ] Choose between function calling and JSON mode for a given task, with reasons
- [ ] Diagnose a structured-output failure as schema violation, hallucinated tool, wrong tool, or argument hallucination
