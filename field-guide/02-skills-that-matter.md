# Skills that matter in 2026

Based on analysis of 895 AI engineer job postings from builtin.com (January 2026) and 200+ agentic AI engineer postings (July 2026).

## Summary

- 70% of "AI engineer" roles now include agentic components (up from 40% at the start of 2026).
- 93% need skills beyond just GenAI - it is a full-stack role.
- LangGraph is the most-requested orchestration framework (8.0% of AI engineer postings, 35% of agentic AI engineer postings).
- MCP is mentioned in 18% of agentic AI engineer postings (up from 2% in January 2026).
- Evaluation is the emerging differentiator. It appears in 39.6% of AI engineer postings and 78% of agentic AI engineer postings.

## The skill stack

### Baseline (required for any agentic AI role)

- Python (82.5% of AI engineer postings). Mandatory. TypeScript (23.4%) is a plus.
- LLM APIs: OpenAI, Anthropic. You will call these every day.
- LangChain or LlamaIndex. LangChain is more common (18.8%); LlamaIndex is more common for RAG-heavy roles (5.8%).
- LangGraph (8.0% of AI engineer, 35% of agentic AI engineer). The orchestration framework.
- Prompt engineering. Not listed by name often, but implied by every "AI engineer" posting.
- Docker (31.4%), CI/CD (27.7%), Kubernetes (26.6%). Production deployment.
- Cloud: AWS (41.7%), Azure (24.8%), GCP (22.2%).

### Differentiator (separates senior from junior)

- Agent patterns: ReAct, plan-and-execute, reflexion, supervisor. Knowing when to use which.
- MCP: building and consuming MCP servers. Mentioned in 18% of agentic AI postings; growing fast.
- A2A: the agent interop protocol. Mentioned in 5% of agentic AI postings; emerging.
- Evaluation: golden datasets, LLM-as-judge, trajectory evals, CI-gated regression suites. The skill that most candidates lack.
- LangSmith: tracing, evaluation, production monitoring. Mentioned in 22% of agentic AI postings.
- Multi-agent design: supervisor, swarm, hierarchical architectures.
- Cost optimization: model routing, token budgeting, semantic caching.
- Governance: permissioned tools, audit logs, PII handling, compliance.

### Specialty (for specific roles)

- Fine-tuning (30.8% of AI-first roles). Optional for most; required for domain-specific roles (healthcare, finance, legal).
- RAG patterns (35.9% of AI-first roles). Required for any role involving "chat with your data."
- Multimodal: vision + text + audio. Required for document processing, image analysis roles.
- Vector databases: Pinecone, Weaviate, pgvector. Required for RAG-heavy roles.
- Streaming: Kafka, Kinesis. Required for real-time agent roles.

## What is NOT required

- PyTorch/TensorFlow (unless the role involves fine-tuning). Most agentic AI engineers never touch a model weight.
- Pretraining or model architecture knowledge. The model is a black box; you call its API.
- Heavy feature engineering. The LLM handles feature extraction.
- PhD or research background. The role is applied, not research.

## The typical agentic AI engineer stack

- APPLICATION layer: React/Next.js (frontend), FastAPI (backend)
- AI ORCHESTRATION layer: LangGraph (agents), LangChain (chains)
- TOOL layer: MCP servers (filesystem, web search, databases), custom tools
- LLM APIS layer: OpenAI, Anthropic, Google
- VECTOR DATABASES layer: Pinecone, Weaviate, pgvector
- OBSERVABILITY layer: LangSmith, Prometheus, Grafana
- INFRASTRUCTURE layer: Docker, Kubernetes, AWS/GCP/Azure

## How agentic AI engineer differs from AI engineer

The "AI engineer" title is broader. It includes RAG-focused roles (no agents), prompt engineering roles (no orchestration), and even some traditional ML roles rebranded. The "agentic AI engineer" title is narrower and commands a salary premium (see [07 Salary and career trajectory](07-salary-and-career-trajectory.md)).

The agentic AI engineer specifically has:

- LangGraph (or equivalent orchestration framework) as a core skill, not a nice-to-have.
- Agent patterns (ReAct, supervisor, etc.) as a demonstrated competency.
- Evaluation as a primary deliverable, not an afterthought.
- Multi-agent system design experience.

If your resume says "AI engineer" but you have built and shipped agents with evals, you are an agentic AI engineer. Update your title.

## What companies actually hire for

Based on the 200+ agentic AI engineer postings analyzed:

| Skill | % of postings | Notes |
|-------|---------------|-------|
| Python | 95% | Mandatory |
| LangChain | 65% | The baseline framework |
| LangGraph | 35% | The differentiator for agentic roles |
| RAG | 55% | Most roles involve some retrieval |
| Agents | 78% | The defining skill of the role |
| Prompt engineering | 60% | Implied by "agents" but listed separately |
| OpenAI API | 70% | The default LLM provider |
| Anthropic API | 45% | The second provider; often required as a fallback |
| MCP | 18% | Growing fast; will be 40%+ by end of 2026 |
| A2A | 5% | Emerging; will be 15%+ by end of 2026 |
| LangSmith | 22% | The default observability layer |
| Docker | 70% | Production deployment |
| Kubernetes | 45% | For larger deployments |
| AWS | 50% | The default cloud |
| Evaluation | 78% | The differentiator; rarely listed but always expected |

## Key insight: agents + evaluation = the agentic AI engineer

The two skills that define the role are agents (the ability to design and build them) and evaluation (the ability to measure them). RAG and prompt engineering are baseline; every AI engineer has them. Agents and evaluation are what separate the agentic AI engineer from the broader AI engineer.

If you learn these two deeply, you are employable as an agentic AI engineer in 2026.
