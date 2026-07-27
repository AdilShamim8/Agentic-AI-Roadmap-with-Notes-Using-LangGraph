# 01 - Foundations

The conceptual and technical base everything else rests on. Read this module first if you are new to agentic AI or if you have been using LangChain casually and want to understand why LangGraph exists.

## What you will learn

- The difference between a chain, a workflow, and an agent, and when to use each
- Why LangGraph exists and what it adds over plain LangChain
- LLM fundamentals at the level an agent engineer needs (no pretraining math)
- Prompt engineering for structured outputs and tool calling
- Structured outputs and tool calling as the bridge between LLMs and software

## Chapters

- [01 What is agentic AI](01-what-is-agentic-ai.md) - definitions, anatomy, the chain-to-agent spectrum
- [02 Why LangGraph](02-why-langgraph.md) - what LangChain cannot do, what LangGraph adds, when to use which
- [03 LLM fundamentals](03-llm-fundamentals.md) - tokenization, context windows, logprobs, model selection
- [04 Prompt engineering](04-prompt-engineering.md) - system vs. user prompts, few-shot in tool descriptions, prompt versioning
- [05 Structured outputs and tool calling](05-structured-outputs-and-tools.md) - JSON mode, function calling, Pydantic schemas, retry on validation failure

## Prerequisites

- Python 3.10+, comfortable with type hints and `async/await`
- Basic familiarity with calling an API from Python
- An OpenAI or Anthropic API key

## Time

2 to 3 weeks at 2 to 3 hours per day.

## What is next

After this module, you are ready for [02 LangGraph core](../02-langgraph-core/), where you will model your first multi-step LLM workflow as a graph.
