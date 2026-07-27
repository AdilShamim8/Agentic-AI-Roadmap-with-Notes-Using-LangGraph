# Docker deployment

Module: 08-production
Chapter: 02-docker-deployment
Status: stable
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Write a Dockerfile for a LangGraph agent
- Write a docker-compose.yml that runs the agent, Postgres (for checkpointing), and Redis (for caching)
- Configure a `langgraph.json` for self-hosted deployment
- Run the agent locally with one command: `docker compose up`

## Prerequisites

- [01 LangGraph Platform](01-langgraph-platform.md)

## Conceptual foundation

Self-hosted Docker is the alternative to LangGraph Platform. You run the LangGraph server in a Docker container, with Postgres for checkpointing (and the Store) and Redis for caching. The setup is more work than the platform, but you control the infrastructure, the data stays in your environment, and there is no per-request fee.

The components:

1. The LangGraph server Docker image. LangChain publishes a pre-built image (`langchain/langgraph:latest`) that runs the LangGraph server. You mount your agent code into the container and point it at your `langgraph.json`.

2. Postgres. Used for checkpointing (durable state) and the Store (long-term memory). A single Postgres instance can serve both.

3. Redis. Optional. Used for caching (semantic cache of tool results) and rate limiting.

4. The `langgraph.json`. Points the server at your agent code, your environment file, and your dependencies.

The Dockerfile is minimal - you do not build a custom image; you use the pre-built one and mount your code. The docker-compose.yml ties together the server, Postgres, and Redis.

## Worked example

The Dockerfile, docker-compose.yml, and langgraph.json for a self-hosted deployment. Full files in [`08-production/`](.).

`Dockerfile`:

```dockerfile
FROM langchain/langgraph:latest

# Copy the agent code
COPY . /app

# Install dependencies
RUN pip install -e /app

# The langgraph.json tells the server where to find the agent
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "8000"]
```

`docker-compose.yml`:

```yaml
version: "3.9"

services:
  langgraph:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - LANGCHAIN_TRACING_V2=true
      - POSTGRES_URL=postgresql://postgres:postgres@postgres:5432/langgraph
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=langgraph
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

`langgraph.json`:

```json
{
  "graphs": {
    "agent": "./examples/conversational_agent_demo.py:agent"
  },
  "env": ".env"
}
```

Run with `docker compose up`. The agent is live at `http://localhost:8000`.

## Evaluation

No eval. The test is: `curl http://localhost:8000/invoke -d '{"messages":[{"role":"user","content":"hi"}]}'` returns a response.

## Production notes

In production, the docker-compose setup needs more: TLS termination (a reverse proxy like nginx or Caddy), authentication (an API key or OAuth), rate limiting (nginx or a dedicated rate limiter), and monitoring (Prometheus + Grafana, or LangSmith). The docker-compose.yml above is the starting point; production adds the surrounding infrastructure.

The most common production failure: the Postgres checkpointer is not configured, so the agent loses state on restart. Fix: always configure `POSTGRES_URL` and use `PostgresSaver` in the agent.

## Common pitfalls

- Using `MemorySaver` in the Dockerfile. Why: it works in dev. Fix: use PostgresSaver for production.
- Not mounting the agent code. Why: the Dockerfile COPY seems sufficient. Fix: use a volume mount in docker-compose for hot reload during dev; COPY for production builds.
- Not configuring TLS. Why: HTTP works. Fix: TLS is required for production; use a reverse proxy.

## Further reading

- [LangGraph self-hosted deployment](https://langchain-ai.github.io/langgraph/cloud/deployment/self_hosted/)
- [LangGraph Docker image](https://hub.docker.com/r/langchain/langgraph)

## Checklist

- [ ] Write a Dockerfile for a LangGraph agent
- [ ] Write a docker-compose.yml with Postgres and Redis
- [ ] Configure a langgraph.json for self-hosted deployment
- [ ] Run the agent locally with `docker compose up`
