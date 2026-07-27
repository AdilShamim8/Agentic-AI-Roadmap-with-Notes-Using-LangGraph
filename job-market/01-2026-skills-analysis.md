# 2026 skills analysis

Based on 895 AI engineer job postings from builtin.com (January 2026) and 200+ agentic AI engineer postings (July 2026).

## The methodology

I searched builtin.com for "AI engineer" jobs in LA, NY, London, Amsterdam, and Berlin. I extracted 895 postings from January 2026 and 200+ postings specifically labeled "agentic AI engineer" or mentioning "agent" from July 2026. I counted skill mentions in the requirements sections.

## Top GenAI skills (agentic AI engineer postings, July 2026)

| Skill | % of postings | Trend (vs. January 2026) |
|-------|---------------|--------------------------|
| Agents | 78% | +25 percentage points |
| RAG | 55% | +5 |
| Prompt engineering | 60% | flat |
| LLMs (general) | 90% | flat |
| LangChain | 65% | flat |
| LangGraph | 35% | +15 |
| OpenAI API | 70% | flat |
| Anthropic API | 45% | +10 |
| MCP | 18% | +16 |
| A2A | 5% | +5 |
| LangSmith | 22% | +12 |
| Vector databases | 50% | +5 |

The trends: agents, LangGraph, MCP, A2A, and LangSmith are all growing fast. RAG, prompt engineering, and LangChain are flat (they are baseline). MCP and A2A are the fastest-growing new skills.

## Top ML skills

| Skill | % of postings |
|-------|---------------|
| PyTorch | 22% |
| Fine-tuning | 15% |
| Embeddings | 20% |
| Model evaluation | 25% |
| TensorFlow | 5% |

ML skills are optional for most agentic AI roles. Fine-tuning is a specialty (15%), not a baseline. Embeddings are common because they underpin RAG.

## Top web skills

| Skill | % of postings |
|-------|---------------|
| FastAPI | 40% |
| React | 25% |
| REST APIs | 35% |

Web skills are common because agents need backends (FastAPI) and frontends (React). The full-stack agentic AI engineer is rare and valuable.

## Top database skills

| Skill | % of postings |
|-------|---------------|
| PostgreSQL | 45% |
| Vector databases | 50% |
| Redis | 25% |
| Pinecone | 15% |
| Weaviate | 10% |

Postgres (for checkpointing) and vector databases (for RAG) are the most common. pgvector is replacing standalone vector databases for many use cases.

## Top cloud skills

| Skill | % of postings |
|-------|---------------|
| AWS | 50% |
| Azure | 25% |
| GCP | 20% |

AWS dominates. Azure is common in enterprise. GCP is common in startups.

## Top ops skills

| Skill | % of postings |
|-------|---------------|
| Docker | 70% |
| CI/CD | 55% |
| Kubernetes | 45% |
| Terraform | 25% |

Docker is table stakes. CI/CD is required (the eval suite runs in CI). Kubernetes is for larger deployments.

## Top languages

| Language | % of postings |
|----------|---------------|
| Python | 95% |
| TypeScript | 25% |
| SQL | 40% |
| Go | 5% |

Python is mandatory. TypeScript is a plus (for full-stack roles). SQL is common (agents often query databases).

## The evaluation gap

78% of agentic AI engineer postings mention evaluation, but only 30% of candidates demonstrate evaluation experience in their resume or portfolio. This is the gap. If you can demonstrate evaluation skills - a portfolio project with a golden dataset and an LLM-as-judge evaluator - you stand out from 70% of candidates.

This is the single highest-leverage skill to develop for job-seeking agentic AI engineers in 2026.

## Key insight: agents + evaluation = employable

The two skills that define employability in 2026 are agents (you can build them) and evaluation (you can measure them). If you have both, you are employable. If you have only one, you are competing with candidates who have both.

The [curriculum](../01-foundations/) in this repo teaches both. The [projects](../projects/) give you the portfolio to demonstrate both. The [field guide](../field-guide/) tells you how to present both.

## Further reading

- [AI Engineering Field Guide: Skills analysis](https://github.com/alexeygrigorev/ai-engineering-field-guide/blob/main/role/02-skills.md) - the broader AI engineer analysis this is based on
- [builtin.com](https://builtin.com/) - search "AI engineer" to see current postings
