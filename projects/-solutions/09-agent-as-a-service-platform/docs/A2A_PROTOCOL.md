# A2A Protocol Reference

This document describes how the Agent-as-a-Service Platform implements the A2A (Agent-to-Agent) protocol. A2A is an open protocol (originally proposed by Google) for interoperability between AI agents.

## Core concepts

### Agent Card

Every A2A-compliant agent exposes a JSON document at:

```
GET /.well-known/agent.json
```

This is the **discovery mechanism**. Clients fetch this card to learn what the agent can do, how to authenticate, and where to send requests.

#### Example Agent Card

```json
{
  "schema_version": "1.0",
  "name": "Research Agent",
  "description": "Answers factual questions about A2A, LangGraph, and more.",
  "version": "1.0.0",
  "url": "http://localhost:8081",
  "protocol_version": "0.3",
  "capabilities": {
    "streaming": false,
    "push_notifications": false,
    "state_transition": true
  },
  "default_input_modes": ["text"],
  "default_output_modes": ["text"],
  "skills": [
    {
      "id": "researcher",
      "name": "Researcher",
      "description": "Knowledge-base QA",
      "tags": ["research", "qa"],
      "input_modes": ["text"],
      "output_modes": ["text"]
    }
  ],
  "authentication": {
    "schemes": ["bearer"]
  },
  "provider": {
    "organization": "A2A Platform Samples",
    "url": "http://localhost:3000"
  }
}
```

### Skills

A skill is a named capability of an agent. An agent can have many skills. Each skill declares:
- `id` — a stable identifier used in requests
- `name` — human-readable name
- `description` — what the skill does
- `tags` — for search/discovery
- `input_modes` / `output_modes` — supported modalities (text, image, audio, etc.)

### Capabilities

Capabilities are protocol-level features the agent supports:
- `streaming` — can stream partial results via SSE
- `push_notifications` — can call back to a webhook when a long task finishes
- `state_transition` — supports stateful sessions (task state machine)

## JSON-RPC methods

A2A uses JSON-RPC 2.0 over HTTP. The endpoint is the agent's `url` (POST `/`).

### `tasks/send`

Send a message to the agent and (synchronously) receive a response.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "tasks/send",
  "params": {
    "id": "task-abc-123",
    "sessionId": "session-xyz",
    "message": {
      "role": "user",
      "parts": [
        { "type": "text", "text": "What is A2A?" }
      ]
    },
    "metadata": {
      "skill_id": "researcher"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "id": "task-abc-123",
    "status": { "state": "completed" },
    "messages": [
      {
        "role": "user",
        "parts": [{ "type": "text", "text": "What is A2A?" }]
      },
      {
        "role": "agent",
        "parts": [
          { "type": "text", "text": "A2A is an open protocol for agent interoperability..." }
        ],
        "timestamp": "2025-01-01T12:00:00Z"
      }
    ],
    "artifacts": [],
    "metadata": {
      "duration_ms": 53,
      "skill_id": "researcher"
    }
  }
}
```

### `tasks/get`

Fetch the current state of a task (useful for long-running tasks).

```json
{
  "jsonrpc": "2.0",
  "id": "req-124",
  "method": "tasks/get",
  "params": { "id": "task-abc-123" }
}
```

### `tasks/cancel`

Cancel a running task.

```json
{
  "jsonrpc": "2.0",
  "id": "req-125",
  "method": "tasks/cancel",
  "params": { "id": "task-abc-123" }
}
```

## Task states

Tasks follow a state machine:

```
pending → running → completed
                ↘ → failed
                ↘ → canceled
                ↘ → timeout
```

The state is returned in `result.status.state`.

## Authentication

The Agent Card declares `authentication.schemes`. The most common scheme is `bearer`, which means clients pass a JWT in the `Authorization` header:

```
Authorization: Bearer <jwt>
```

In this platform, the JWT is obtained from `POST /auth/login` on the backend. The backend then proxies A2A calls to the agent runtime, attaching the user's identity in the JSON-RPC `metadata` field.

## Streaming (optional capability)

If `capabilities.streaming` is `true`, the agent supports Server-Sent Events (SSE) on `tasks/send` (when `stream: true` is set in the request). Each SSE event is a JSON-RPC response chunk with incremental `messages` or `artifacts`.

This reference implementation does not implement streaming — `capabilities.streaming` is `false`.

## Push notifications (optional capability)

If `capabilities.push_notifications` is `true`, the client can register a callback URL in the request, and the agent will POST the final result there when the task completes. Useful for long-running tasks (minutes to hours).

This reference implementation does not implement push notifications.

## How this platform uses A2A

| Component | Role |
|-----------|------|
| Agent runtime | A2A server — serves Agent Card, handles JSON-RPC |
| FastAPI backend | A2A client — proxies user requests via JSON-RPC, records invocations |
| A2A gateway | A2A aggregator — serves a directory Agent Card, routes calls to per-agent runtimes |
| Frontend | Calls the backend's REST API, which abstracts away A2A |

## Compliance checklist

An agent is A2A-compliant if it:

- [x] Serves `GET /.well-known/agent.json` returning a valid Agent Card
- [x] Accepts `POST /` with JSON-RPC 2.0 payloads
- [x] Implements `tasks/send` (synchronous mode)
- [x] Returns a `result` with `id`, `status`, `messages`, and `artifacts`
- [x] Honors the `authentication.schemes` declared in the card
- [x] Sets `protocol_version` to a supported version (currently `0.3`)

## References

- A2A spec (community draft): https://github.com/google/agent2agent
- Agent Card JSON schema: see `backend/schemas/agent.py` in this repo
- Sample implementation: see `agent-runtime/server.py`
