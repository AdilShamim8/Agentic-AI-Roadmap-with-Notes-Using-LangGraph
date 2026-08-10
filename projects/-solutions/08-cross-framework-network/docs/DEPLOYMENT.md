# Deployment Guide

## Local Development

### Prerequisites

- Python 3.10 or later
- `pip` and `venv`

### Setup

```bash
# 1. Clone and enter the project
cd 08-cross-framework-network

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
make install   # or: pip install -e ".[dev]"

# 4. Copy environment template
cp .env.example .env
```

### Running Locally

#### Three terminals (recommended for development)

```bash
# Terminal 1: Research agent
python -m agents.openai_research.server --port 8001

# Terminal 2: Writer crew
python -m agents.crewai_writer.server --port 8002

# Terminal 3: Supervisor
python -m supervisor.cli "Research and write about A2A protocol"
```

#### Single command (background agents)

```bash
make start-agents        # starts both agents in background
make supervisor TASK="Research and write about A2A protocol"
make stop-agents         # stops background agents
```

#### Demo (all-in-one)

```bash
make demo   # starts agents, runs a demo task, prints results
```

## Docker Deployment

### Build and run

```bash
# Build images
docker compose build

# Start agent servers
docker compose up -d research-agent writer-crew

# Run the supervisor on a task
docker compose run --rm supervisor "Research multi-agent AI and write a blog post"

# Run the evaluation
docker compose run --rm supervisor python -m eval.runner --limit 5

# Stop everything
docker compose down
```

### Health checks

Both agent services have health checks configured:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8001/.well-known/agent.json"]
  interval: 10s
  timeout: 5s
  retries: 5
```

The supervisor's `depends_on` with `condition: service_healthy` ensures agents are ready before the supervisor runs.

### Viewing logs

```bash
docker compose logs -f research-agent
docker compose logs -f writer-crew
docker compose logs -f supervisor
```

## Production Considerations

### Using a Real LLM

Set environment variables (in `.env` or Docker environment):

```bash
LLM_BACKEND=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o
```

For Docker:
```bash
# .env file
LLM_BACKEND=openai
OPENAI_API_KEY=sk-your-key-here

# docker compose picks up .env automatically
docker compose up -d research-agent writer-crew
```

### Scaling

Each agent is an independent HTTP service. To scale:

1. **Run multiple instances** behind a load balancer (nginx, HAProxy):
   ```nginx
   upstream research_agents {
     server research-agent-1:8001;
     server research-agent-2:8001;
     server research-agent-3:8001;
   }
   ```

2. **Update supervisor URLs** to point at the load balancer:
   ```bash
   RESEARCH_AGENT_URL=http://lb:8001
   WRITING_AGENT_URL=http://lb:8002
   ```

3. **Use container orchestration** (Kubernetes, ECS) for auto-scaling.

### Security

The reference implementation has **no authentication** — it's designed for local/development use. For production:

1. **Add API key authentication** to A2A endpoints:
   ```python
   @app.middleware("http")
   async def auth_middleware(request: Request, call_next):
       if request.headers.get("X-API-Key") != os.environ["A2A_API_KEY"]:
           return JSONResponse({"error": "Unauthorized"}, status_code=401)
       return await call_next(request)
   ```

2. **Use HTTPS** (TLS termination at a reverse proxy)

3. **Rate-limit** per-client to prevent abuse

4. **Validate and sanitize** all task inputs

5. **Use secrets management** for API keys (Vault, AWS Secrets Manager)

### Observability

#### Logging

Set `LOG_LEVEL` to control verbosity:
- `DEBUG` — verbose, includes all A2A requests/responses
- `INFO` — default, shows task lifecycle and handoffs
- `WARNING` — only errors and warnings
- `ERROR` — errors only

#### LangSmith Tracing (optional)

For distributed tracing across A2A boundaries:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsyour-key-here
LANGSMITH_PROJECT=cross-framework-network
```

#### Metrics

The evaluation framework captures:
- Task completion rate
- Interop correctness (handoff success rate)
- Average/max handoff latency
- Cost overhead percentage

Results are saved to `eval/results/eval_results.json`.

### CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest tests/ -v
      - run: python -m examples.demo  # smoke test
```

## Troubleshooting

### "Connection refused" when running supervisor

The agent servers aren't running or aren't ready. Start them first:

```bash
make start-agents
# wait a few seconds, then:
make supervisor TASK="..."
```

### Agent server won't start

Check if the port is already in use:

```bash
lsof -i :8001  # check port 8001
lsof -i :8002  # check port 8002
```

Use a different port if needed:

```bash
python -m agents.openai_research.server --port 9001
RESEARCH_AGENT_URL=http://localhost:9001 python -m supervisor.cli "task"
```

### Tests fail with import errors

Ensure the project is installed in development mode:

```bash
pip install -e ".[dev]"
```

### Docker build fails

Ensure Docker has enough resources (at least 2GB RAM). Clean up and rebuild:

```bash
docker compose down -v
docker system prune -f
docker compose build --no-cache
```

### OpenAI API errors

If using `LLM_BACKEND=openai`:
- Verify `OPENAI_API_KEY` is set correctly
- Check your API quota and rate limits
- Ensure the `openai` package is installed: `pip install openai`
