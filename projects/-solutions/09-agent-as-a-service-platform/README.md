# Agent-as-a-Service Platform

> A marketplace platform where users can deploy, discover, and invoke AI agents via the A2A (Agent-to-Agent) protocol — with usage tracking, billing, and quality ratings.

Difficulty: ⭐⭐⭐⭐⭐
Estimated build time: 4–6 weeks
Status: reference implementation

---

## What this is

This is the "app store for agents": users browse Agent Cards, deploy their own agents, invoke them through a unified A2A gateway, and get billed per invocation. The platform exercises A2A at scale, platform engineering, and marketplace concepts.

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
│  Next.js UI  │ ───► │  FastAPI     │ ───► │  A2A Gateway     │
│  (browse,    │ HTTP │  (auth, API, │      │  (agent.json +   │
│   deploy,    │ ◄─── │   billing)   │ ◄─── │   task routing)  │
│   usage)     │      └──────┬───────┘      └────────┬─────────┘
└──────────────┘             │                       │
                             │                       ▼
                ┌────────────▼───────────┐   ┌──────────────────┐
                │  Postgres              │   │  Agent Runtime    │
                │  (users, agents,       │   │  (Docker per      │
                │   invocations, billing)│   │   deployed agent) │
                └────────────────────────┘   └──────────────────┘
                             │
                ┌────────────▼───────────┐   ┌──────────────────┐
                │  Stripe (billing)      │   │  Prometheus +    │
                │                        │   │  Grafana (metrics)│
                └────────────────────────┘   └──────────────────┘
```

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Agent runtime | Docker containers (one per deployed agent) |
| A2A gateway | FastAPI service serving `/.well-known/agent.json` |
| Database | Postgres 16 |
| Billing | Stripe (test mode) |
| Observability | Prometheus + Grafana |
| Auth | JWT (HS256) |
| Container | Docker Compose |

## Repository layout

```
agent-as-a-service-platform/
├── frontend/              # Next.js web UI
├── backend/               # FastAPI API server
├── agent-runtime/         # Sample A2A-compliant agent runtime
├── a2a-gateway/           # A2A protocol gateway (agent.json + routing)
├── infra/                 # Postgres, Prometheus, Grafana configs
├── docs/                  # Architecture + A2A protocol docs
├── docker-compose.yml     # Orchestrates every service
├── .env.example           # Copy to .env and fill in
└── scripts/               # Helper scripts (seed, deploy-agent, etc.)
```

## Quickstart

### Prerequisites

- Docker 24+
- Docker Compose v2
- Node 18+ (only for local frontend dev)
- Python 3.11+ (only for local backend dev)

### 1. Clone and configure

```bash
git clone <this-repo>
cd agent-as-a-service-platform
cp .env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD and a JWT_SECRET
```

### 2. Boot the whole stack

```bash
docker compose up --build
```

This starts:
- Postgres on `:5432`
- FastAPI on `:8000`  (Swagger at http://localhost:8000/docs)
- Next.js on `:3000`
- A2A Gateway on `:8080`
- A sample agent runtime on `:8081`
- Prometheus on `:9090`
- Grafana on `:3001`

### 3. Seed sample agents

```bash
./scripts/seed.sh
```

This registers 5 sample agents (researcher, coder, summarizer, translator, data-analyst) in the database and spins up their runtimes.

### 4. Open the UI

Visit http://localhost:3000 — browse agents, view Agent Cards, deploy your own, and see usage.

## A2A protocol

Every deployed agent exposes an Agent Card at:

```
GET http://<agent-host>/.well-known/agent.json
```

The card declares the agent's identity, capabilities, endpoints, and auth. See [`docs/A2A_PROTOCOL.md`](docs/A2A_PROTOCOL.md) for the full spec.

## API overview

See http://localhost:8000/docs for interactive Swagger. Highlights:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create a user |
| `POST` | `/auth/login` | Get a JWT |
| `GET` | `/agents` | List all deployed agents |
| `GET` | `/agents/{id}` | Get one agent + its Agent Card |
| `POST` | `/agents` | Deploy a new agent (upload Docker image) |
| `POST` | `/agents/{id}/invoke` | Invoke an agent via A2A |
| `GET` | `/usage` | Per-user usage stats |
| `POST` | `/billing/checkout` | Start Stripe checkout |
| `GET` | `/.well-known/agent.json` | (Gateway) Aggregate Agent Card |

## Eval rubric (from spec)

| Metric | Target | How measured |
|--------|--------|--------------|
| Agent deployment time | < 5 min | From upload to live |
| A2A compliance | 100% | Deployed agents pass A2A spec test |
| Platform uptime | 99.5%+ | Monthly uptime |
| Cold-start latency | < 3s | For an idle agent |
| Per-agent cost tracking | 100% | All invocations attributed and billed |

## Development

### Run frontend only

```bash
cd frontend
npm install
npm run dev
```

### Run backend only

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Run tests

```bash
cd backend && pytest
```

## License

MIT — see `LICENSE`.
