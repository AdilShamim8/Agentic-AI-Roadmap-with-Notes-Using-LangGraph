# API Reference

Interactive Swagger docs are available at http://localhost:8000/docs once the backend is running.

This document is a human-readable summary.

## Authentication

All endpoints except `POST /auth/register`, `POST /auth/login`, and `GET /health` require a JWT in the `Authorization` header:

```
Authorization: Bearer <token>
```

### `POST /auth/register`

Create a new user account.

**Body:**
```json
{
  "email": "you@example.com",
  "username": "yourname",
  "password": "at-least-8-chars",
  "full_name": "Optional Display Name"
}
```

**Response (201):**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": "...", "email": "...", "username": "...", ... }
}
```

### `POST /auth/login`

Exchange credentials for a JWT.

**Body:**
```json
{ "email": "you@example.com", "password": "..." }
```

**Response (200):** same shape as register.

### `GET /auth/me`

Return the currently authenticated user.

---

## Agents

### `GET /agents`

List all deployed agents.

**Query params:**
- `q` (string) — search by name or description
- `status` (enum) — filter by status (default: `running`)
- `limit` (int, default 50, max 200)
- `offset` (int, default 0)

**Response (200):** array of `AgentOut`.

### `GET /agents/{agent_id}`

Get a single agent.

### `GET /agents/{agent_id}/card`

Get the A2A Agent Card for this agent.

**Response:** an `AgentCard` JSON object (see `docs/A2A_PROTOCOL.md`).

### `POST /agents`

Deploy a new agent.

**Body:**
```json
{
  "name": "Weather Forecaster",
  "description": "Returns weather forecasts for any city.",
  "version": "1.0.0",
  "docker_image": "ghcr.io/myorg/weather-agent:latest",
  "price_per_invocation_cents": 5,
  "skills": [
    {
      "id": "forecast",
      "name": "Forecast",
      "description": "Get the forecast for a city",
      "tags": ["weather"]
    }
  ]
}
```

**Response (201):**
```json
{
  "agent": { "id": "...", "status": "pending", ... },
  "message": "Deployment started. Poll /agents/{id} for status."
}
```

### `POST /agents/{agent_id}/invoke`

Invoke the agent via A2A.

**Body:**
```json
{
  "message": "What's the weather in Tokyo?",
  "skill_id": "forecast",
  "metadata": { "session_id": "..." },
  "stream": false
}
```

**Response (200):**
```json
{
  "invocation_id": "...",
  "a2a_task_id": "...",
  "status": "completed",
  "output": "Tokyo: 18°C, partly cloudy...",
  "duration_ms": 423,
  "cost_cents": 5
}
```

### `PATCH /agents/{agent_id}`

Update an agent (owner or admin only).

### `DELETE /agents/{agent_id}`

Undeploy and remove an agent (owner or admin only).

### `POST /agents/{agent_id}/ratings`

Rate an agent (1-5 stars).

**Body:**
```json
{ "score": 5, "review": "Fast and accurate!" }
```

### `GET /agents/{agent_id}/ratings`

List all ratings for an agent.

---

## Invocations

### `GET /invocations`

List the current user's invocations.

**Query params:**
- `agent_id` (UUID) — filter by agent
- `limit`, `offset`

### `GET /invocations/{invocation_id}`

Get a single invocation (with full input/output).

---

## Billing

### `GET /billing/usage`

Get aggregated usage stats for the current user.

**Response:**
```json
{
  "total_invocations": 142,
  "total_cost_cents": 710,
  "invocations_this_month": 23,
  "cost_this_month_cents": 115,
  "plan": "starter",
  "invocations_used": 23,
  "invocations_included": 1000,
  "by_agent": [
    { "agent_id": "...", "name": "Coder", "count": 15, "cost_cents": 75 }
  ]
}
```

### `GET /billing/subscription`

Get the current user's subscription.

### `POST /billing/checkout?plan=starter`

Create a Stripe Checkout session for upgrading to a plan.

**Response:**
```json
{ "checkout_url": "https://checkout.stripe.com/...", "session_id": "cs_..." }
```

In mock mode (no Stripe key configured), returns a URL pointing at the frontend billing page.

### `POST /billing/upgrade?plan=pro`

Mock upgrade (for dev without Stripe). Instantly changes the user's plan.

### `POST /billing/webhook`

Stripe webhook receiver. Verifies the signature if `STRIPE_WEBHOOK_SECRET` is set.

Configure in your Stripe dashboard to point at:
```
https://your-domain.com/billing/webhook
```

Events handled:
- `checkout.session.completed` — activates the subscription
- (extend as needed)

---

## Internal (used by the A2A gateway)

These endpoints are not authenticated and should be firewalled off from public access in production.

### `GET /internal/agents`

Return all running agents with their base URLs.

### `GET /internal/agents/{agent_id}`

Return a single agent's full record.

### `PATCH /internal/agents/{agent_id}/status`

Update an agent's status (used by the agent_runtime service after deploy).

---

## Health & metrics

### `GET /health`

Liveness probe. Always returns 200.

### `GET /health/ready`

Readiness probe. Checks Postgres connectivity.

### `GET /metrics`

Prometheus scrape endpoint. Exposes counters and histograms.

---

## Error format

All errors return JSON:

```json
{
  "detail": "Human-readable error message"
}
```

Common status codes:
- `400` — bad request (validation error)
- `401` — not authenticated
- `403` — not authorized (e.g. not the owner)
- `404` — resource not found
- `409` — conflict (e.g. agent not in running state)
- `422` — Pydantic validation error (response has `detail` array)
- `502` — upstream failure (agent unreachable, Stripe down)
- `503` — service unavailable
