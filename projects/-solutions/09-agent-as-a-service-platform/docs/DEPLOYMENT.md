# Deployment Guide

This guide covers local development, Docker Compose deployment, and notes on production deployment.

## Local development

### Prerequisites

- Docker 24+ with Docker Compose v2
- (Optional, for native dev) Node 18+, Python 3.11+

### Step 1: Configure

```bash
cp .env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD and JWT_SECRET
```

### Step 2: Boot the stack

```bash
docker compose up --build
```

The first build takes ~3-5 minutes. Subsequent starts are ~10 seconds.

Wait until you see:
- `a2a-backend    | INFO:     Uvicorn running on http://0.0.0.0:8000`
- `a2a-frontend   | ▲ Next.js 14.2.5`
- `a2a-gateway    | INFO:     Uvicorn running on http://0.0.0.0:8080`

### Step 3: Seed sample agents

```bash
./scripts/seed.sh
```

This registers a demo user (`demo@a2a.local` / `demo-pass-123`) and deploys 5 sample agents.

### Step 4: Open the UI

Visit http://localhost:3000

- Browse agents
- Sign in with the demo credentials
- Click an agent and try invoking it

### Step 5: Check observability

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin / admin)
- FastAPI Swagger: http://localhost:8000/docs

## Native development (without Docker)

If you want to develop the frontend or backend natively:

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start Postgres separately (e.g. via docker run)
docker run -d --name a2a-pg -p 5432:5432 \
  -e POSTGRES_USER=a2a -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=a2a_platform postgres:16-alpine

# Run migrations
alembic upgrade head

# Start the dev server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Agent runtime

```bash
cd agent-runtime
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8081
```

## Production deployment

This reference implementation is not production-ready. Here's what you'd need to change:

### Infrastructure

- **Compute**: Kubernetes (EKS/GKE/AKS) or a PaaS like Render/Railway
- **Database**: Managed Postgres (RDS, Cloud SQL, Neon) with automated backups
- **Container registry**: ECR / GCR / GHCR for agent images
- **Load balancer**: ALB / Cloudflare in front of the frontend and API
- **Secrets**: Vault / AWS Secrets Manager / k8s Secrets (NOT `.env` files)

### Security hardening

- Move JWT from localStorage to httpOnly cookies
- Add CSRF protection
- Enable rate limiting on auth endpoints (`slowapi` or a WAF)
- Use Stripe webhook signature verification (set `STRIPE_WEBHOOK_SECRET`)
- Restrict Docker socket access (or use a separate deployer service)
- Add WAF (Cloudflare / AWS WAF) in front
- Enable HTTPS everywhere (Let's Encrypt / ACM)

### Scaling

- Run multiple backend replicas behind ALB
- Use PgBouncer for connection pooling
- Add Redis for:
  - Session storage
  - Rate limiting
  - Celery task queue for async deployments
- Horizontal Pod Autoscaler for the frontend
- Pre-warm agent containers to reduce cold-start latency

### Observability

- Add Sentry for error tracking
- Add OpenTelemetry tracing (export to Tempo / Honeycomb / Datadog)
- Long-term Prometheus storage (Thanos / Mimir)
- Log aggregation (Loki / CloudWatch Logs)

### CI/CD

Suggested GitHub Actions workflow:

```yaml
name: CI
on: [push, pull_request]
jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres: ...
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r backend/requirements.txt
      - run: cd backend && pytest

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci && npm run build

  docker-build:
    needs: [backend-test, frontend-build]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [backend, frontend, a2a-gateway, agent-runtime]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: ./${{ matrix.service }}
          push: true
          tags: ghcr.io/yourorg/a2a-${{ matrix.service }}:latest
```

## Troubleshooting

### `docker compose up` fails with port conflict

Change the port mapping in `docker-compose.yml`. For example, to change the frontend port:

```yaml
frontend:
  ports:
    - "3005:3000"  # host:container
```

### Backend can't reach Postgres

Check that `POSTGRES_HOST` is set to `postgres` (the service name in docker-compose) — not `localhost`.

### Stripe webhooks not arriving

Use the Stripe CLI to forward webhooks in dev:

```bash
stripe listen --forward-to http://localhost:8000/billing/webhook
```

### Agent invocation returns 502

The agent runtime may not be running. Check:

```bash
docker compose logs agent-runtime
docker compose logs backend | grep "agent_runtime"
```

### `alembic upgrade head` fails

If the database is in an inconsistent state, wipe and recreate:

```bash
docker compose down -v  # WARNING: destroys all data
docker compose up --build
```

## Cleanup

```bash
# Stop all services (keep data)
docker compose down

# Stop all services AND wipe all data
docker compose down -v

# Remove dangling images
docker image prune -f
```
