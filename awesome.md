# Awesome Agentic AI

A curated list of resources for building agentic AI systems. Compiled while researching content for this roadmap. Every entry earned its place by being cited from at least one chapter, project, or field-guide file in this repo.

## Foundational papers

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) - the foundational Reasoning + Acting pattern. Every agent framework implements some variant of this.
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) - self-improving agents via verbal self-critique.
- [Tree of Thoughts](https://arxiv.org/abs/2305.10601) - deliberate, structured problem solving as an alternative to linear chain-of-thought.
- [LATS: Language Agent Tree Search](https://arxiv.org/abs/2310.04406) - tree search over agent trajectories for complex planning.
- [Agent-as-a-Judge: Agents Evaluating Agents](https://arxiv.org/abs/2410.10934) - using agents to evaluate agents at scale. Core to modern eval pipelines.
- [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761) - the paper that established tool-use as a learned capability.

## Frameworks and libraries

- [LangGraph](https://github.com/langchain-ai/langgraph) - the orchestration framework this roadmap is built around. Stateful graphs, checkpointing, HITL.
- [LangChain](https://github.com/langchain-ai/langchain) - the underlying library. LCEL, chat models, document loaders.
- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters) - the bridge between MCP servers and LangGraph agents.
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) - OpenAI's native agent framework. Used for cross-framework interop examples.
- [CrewAI](https://github.com/crewAIInc/crewAI) - role-based multi-agent framework. Used for cross-framework interop examples.
- [AutoGen](https://github.com/microsoft/autogen) - Microsoft's conversational multi-agent framework. Research-oriented.
- [LlamaIndex](https://github.com/run-llama/llama_index) - data ingestion and RAG framework. Used in the knowledge manager project.
- [Pydantic](https://github.com/pydantic/pydantic) - the schema validation library that underpins structured outputs.

## Protocols

- [Model Context Protocol specification](https://spec.modelcontextprotocol.io/) - the open protocol for tool and context interop.
- [MCP servers registry](https://github.com/modelcontextprotocol/servers) - pre-built, ready-to-use MCP tool servers.
- [A2A protocol specification](https://google.github.io/A2A/) - the open protocol for agent-to-agent communication.
- [google/A2A](https://github.com/google/A2A) - reference implementations and SDKs.

## Observability and eval

- [LangSmith](https://smith.langchain.com/) - tracing, evaluation datasets, production monitoring. The default observability layer for this roadmap.
- [LangGraph Studio](https://github.com/langchain-ai/langgraph-studio) - visual IDE for agent debugging and step-through execution.
- [LangGraph Platform](https://langchain-ai.github.io/langgraph/concepts/langgraph_platform/) - managed deployment, cron, Assistants API.
- [OpenTelemetry](https://opentelemetry.io/) - vendor-neutral tracing. Useful when LangSmith is not an option.

## Practitioner blogs and engineering write-ups

- [Anthropic engineering blog](https://www.anthropic.com/engineering) - especially the posts on building effective agents, tool use, and MCP.
- [LangChain blog](https://blog.langchain.dev/) - release notes, pattern deep-dives, and case studies.
- [Hugging Face blog](https://huggingface.co/blog) - model releases, fine-tuning guides, agent research.
- [Eugene Yan's blog](https://eugeneyan.com/) - applied ML engineering, eval practices, production patterns.
- [Hamel Husain's blog](https://hamel.dev/) - evaluation, testing, and LLM engineering practice.
- [Lilian Weng's blog](https://lilianweng.github.io/) - technical deep-dives on agent architectures, memory, and reasoning.

## Books and courses

- [AI Engineering Buildcamp: From RAG to Agents](https://maven.com/alexey-grigorev/from-rag-to-agents) - 9-week intensive by Alexey Grigorev. The reference style for the field guide in this repo.
- [LangChain Academy](https://academy.langchain.com/) - official courses on LangGraph and multi-agent systems.
- [DeepLearning.AI short courses](https://www.deeplearning.ai/short-courses/) - practical agent-building courses, including "AI Agents in LangGraph."
- [Prompt Engineering Guide](https://www.promptingguide.ai/) - open-source reference for prompt patterns.
- [Hands-On Large Language Models](https://www.oreilly.com/library/view/hands-on-large-language/9781098150952/) - Jay Alammar and Maarten Grootendorst. Practical LLM engineering.

## Real-world case studies

- [How Klarna built a customer-support agent](https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/) - production customer-support agent at scale.
- [Stripe's LLM-powered support tooling](https://stripe.com/blog) - engineering write-ups on agent deployment in fintech.
- [Cursor's agent architecture](https://cursor.com/blog) - coding agents in production.
- [Perplexity's answer engine](https://blog.perplexity.ai/) - multi-source research agents at consumer scale.

## Job market data sources

- [builtin.com](https://builtin.com/) - job postings used for skill analysis in the field guide.
- [AI Engineering Field Guide](https://github.com/alexeygrigorev/ai-engineering-field-guide) - 4,894 job descriptions analyzed. The benchmark for the field guide style in this repo.
- [Levels.fyi](https://www.levels.fyi/) - salary data for AI engineering roles.

## Reference repos to study

- [SEC Insights](https://github.com/run-llama/sec-insights) - RAG over SEC filings with a finance-specific UI.
- [Invoice Extract and Reconcile](https://github.com/run-llama/template-workflow-extract-reconcile-invoice) - structured extraction with typed schemas and review UI.
- [GPT Engineer](https://github.com/AntonOsika/gpt-engineer) - coding agent reference implementation.
- [SWE-agent](https://github.com/princeton-nlp/SWE-agent) - the academic reference for autonomous coding agents.
- [browser-use](https://github.com/browser-use/browser-use) - agentic browser reference implementation.

## Contributing to this list

Open an issue with the resource, why it belongs here, and which chapter or project in the roadmap cites it. Resources without a citation in the roadmap are not added — the list is curated, not exhaustive.
