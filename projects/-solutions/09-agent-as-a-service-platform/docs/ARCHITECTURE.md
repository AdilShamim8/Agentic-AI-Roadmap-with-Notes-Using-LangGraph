# Architecture

This document describes the system architecture of the Agent-as-a-Service Platform, including the data flow, service responsibilities, and key design decisions.

## High-level diagram

```
                          ┌──────────────────────────────────────┐
                          │           User's browser             │
                          └────────────────┬─────────────────────┘
                                           │  HTTP
                                           ▼
                          ┌──────────────────────────────────────┐
                          │   Next.js Frontend  (port 3000)      │
                          │   - Browse / Deploy / Invoke         │
                          │   - Dashboard / Billing UI           │
                          └────────────────┬─────────────────────┘
                                           │  REST + JWT
                                           ▼
                          ┌──────────────────────────────────────┐
                          │   FastAPI Backend  (port 8000)       │
                          │   - Auth (JWT)                       │
                          │   - Agent registry                   │
                          │   - Invocation orchestration         │
                          │   - Billing (Stripe)                 │
                          │   - Metrics (/metrics)               │
                          └─────┬───────────────┬────────────┬───┘
                                │               │            │
                ┌───────────────▼──┐    ┌────────▼─────┐    ┌─▼──────────────┐
                │  Postgres (5432) │    │  A2A Gateway │    │   Stripe API   │
                │  - users         │    │  (port 8080) │    │   (external)   │
                │  - agents        │    └──────┬───────┘    └────────────────┘
                │  - invocations   │           │
                │  - subscriptions │           │ JSON-RPC
                │  - billing       │           ▼
                └──────────────────┘    ┌──────────────────────────┐
                                        │  Agent Runtime (port 8081)│
                                        │  - /.well-known/agent.json│
                                        │  - A2A JSON-RPC handlers  │
                                        │  - sample skills          │
                                        └──────────────────────────┘

              ┌──────────────────────────────────────────────┐
              │   Observability stack                        │
              │   ┌──────────────┐    ┌──────────────────┐   │
              │   │ Prometheus   │───▶│   Grafana        │   │
              │   │ (port 9090)  │    │   (port 3001)    │   │
              │   └──────────────┘    └──────────────────┘   │
              └──────────────────────────────────────────────┘
```

## Service responsibilities

### 1. Frontend (Next.js 14)

- Server-rendered landing page (browse agents) for fast first paint.
- Client-side auth flow using JWT stored in localStorage.
- Agent detail page lets users invoke the agent and view the raw Agent Card.
- Deploy page collects agent metadata (name, Docker image, skills, price).
- Dashboard shows usage charts (recharts) and recent invocations.
- Billing page shows current plan and lets users upgrade via Stripe checkout.

### 2. Backend (FastAPI)

- **Auth**: JWT (HS256), bcrypt password hashing.
- **Agent registry**: CRUD for agents, plus `/internal/agents` for the gateway.
- **Invocation orchestration**: records an `Invocation` row, proxies to the agent runtime via the A2A protocol, records the result, and emits a billing event.
- **Billing**: integrates with Stripe for subscription checkout, and records per-invocation charges as `BillingEvent` rows. Falls back to a mock mode when `STRIPE_SECRET_KEY` is unset.
- **Metrics**: `/metrics` exposes Prometheus counters and histograms.

### 3. A2A Gateway

- Serves an **aggregate Agent Card** at `/.well-known/agent.json` that lists all deployed agents.
- Forwards per-agent A2A calls (`POST /agents/{slug}`) to the correct agent runtime based on the registry.
- This is the single public-facing endpoint that A2A clients would use.

### 4. Agent Runtime

- Sample FastAPI app that implements the A2A v0.3 protocol.
- Serves its own Agent Card at `/.well-known/agent.json`.
- Handles JSON-RPC methods: `tasks/send`, `tasks/get`, `tasks/cancel`.
- Ships with three sample skills: researcher, coder, summarizer.

### 5. Postgres

- Primary data store. Schema managed by Alembic migrations.
- Tables: `users`, `agents`, `agent_versions`, `agent_ratings`, `invocations`, `subscriptions`, `billing_events`.
- Uses `UUID` primary keys and `JSONB` for flexible agent_card / metadata fields.

### 6. Observability (Prometheus + Grafana)

- Prometheus scrapes `/metrics` from backend, gateway, and agent-runtime every 15s.
- Grafana auto-provisions a Prometheus datasource and a "Platform Overview" dashboard.
- Tracked metrics: request rate, p95 latency, agent invocations by agent_id, cold-start latency.

## Data flow: a single agent invocation

1. User clicks "Invoke agent" on the frontend.
2. Frontend sends `POST /agents/{id}/invoke` with the JWT.
3. Backend verifies the JWT, looks up the Agent row, checks `status == running`.
4. Backend creates an `Invocation` row with status `running`.
5. Backend calls `agent_runtime.invoke()`, which issues an A2A JSON-RPC `tasks/send` to the agent's `base_url`.
6. Agent runtime processes the message (e.g. calls the researcher skill) and returns a JSON-RPC result.
7. Backend records the output, sets `status = completed`, updates `invocations_count` on the agent.
8. If the agent has a non-zero price, Backend calls `billing_service.record_invocation_charge()` which:
   - Creates a `BillingEvent` row.
   - Increments the user's `Subscription.invocations_used`.
   - If the user is on the FREE plan and exceeds the cap, marks subscription `past_due`.
9. Backend returns the response to the frontend, which renders the output.

## Design decisions

### Why a separate A2A Gateway?

The gateway serves as the public A2A entry point. Clients who want to use A2A natively (without going through the platform's REST API) can hit the gateway directly. It also serves the aggregate Agent Card — a directory of all deployed agents — which is useful for discovery.

### Why per-invocation billing instead of flat-rate?

Per-invocation billing is the most accurate way to attribute cost. Each `Invocation` row carries a `cost_cents` field, and every charge creates an auditable `BillingEvent`. Subscription plans include a quota; overages could be billed at the metered rate via Stripe UsageRecords.

### Why Docker for the agent runtime?

The spec mentions "LangGraph Platform or self-hosted Docker". We chose Docker because:
- It's the most accessible option for self-hosting.
- The backend talks to the Docker socket directly (`/var/run/docker.sock`) to start/stop agent containers.
- In production, swap this for Kubernetes jobs or a managed runtime like LangGraph Platform, Modal, or Replicate.

### Why JWT in localStorage?

For simplicity in this reference implementation. In production:
- Use httpOnly cookies to prevent XSS token theft.
- Add refresh tokens and short-lived access tokens.
- Consider OAuth2 / OIDC (Auth0, Clerk, WorkOS) for SSO.

### Why Alembic instead of `create_all()`?

`create_all()` doesn't support schema evolution. Alembic gives us versioned migrations so the schema can evolve without data loss. The initial migration (`0001_initial.py`) creates every table.

## Scaling considerations

| Concern | Current | Production |
|---------|---------|-----------|
| Agent invocation routing | Direct HTTP via `agent.base_url` | Service mesh (Istio/Linkerd) or k8s service discovery |
| Container orchestration | Docker SDK, one container per agent | Kubernetes Deployment + HPA per agent |
| Database | Single Postgres | Postgres with read replicas + PgBouncer |
| Billing webhook | Single endpoint | Idempotent webhook with retry + signature verification |
| Metrics | Prometheus pull | Prometheus + long-term storage (Thanos/Mimir) |
| Secrets | `.env` file | Vault / AWS Secrets Manager / k8s Secrets |
| Cold start | Container start ~2-5s | Pre-warmed pool of agent containers |

## Security notes

- **JWT secret** must be a long random string in production.
- **CORS** is locked to the frontend origin.
- **Stripe webhooks** verify signatures when `STRIPE_WEBHOOK_SECRET` is set.
- **Docker socket** mount is a privilege escalation — in production, use a constrained container runtime (gVisor, Kata) or a separate deployer service.
- **SQL injection**: all queries use SQLAlchemy parameterized statements.
- **XSS**: React escapes by default; we don't use `dangerouslySetInnerHTML`.

## Failure modes

| Failure | Detection | Mitigation |
|---------|-----------|-----------|
| Agent container crashes | Health probe in agent_runtime | Restart policy `unless-stopped`; mark agent `failed` after 3 retries |
| Postgres unreachable | `/health/ready` endpoint | Return 503; circuit breaker in backend |
| Stripe API down | Checkout call fails | Fall back to mock mode; queue billing events for retry |
| A2A gateway overloaded | p95 latency alert | Horizontal scaling; cache agent registry |
| Cold start too slow | `a2a_cold_start_ms` metric | Pre-warm pool; container snapshotting |
