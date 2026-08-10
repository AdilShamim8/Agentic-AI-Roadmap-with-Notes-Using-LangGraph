# A2A Protocol Implementation

This document describes the A2A (Agent-to-Agent) protocol implementation in this project.

## What is A2A?

A2A is an open protocol by Google that enables AI agents built on different frameworks to communicate with each other. It defines:

1. **Agent Cards** — a discovery document at `/.well-known/agent.json`
2. **JSON-RPC 2.0** — the message format for all interactions
3. **Task lifecycle** — a state machine for managing work between agents
4. **Streaming** — Server-Sent Events (SSE) for real-time updates

## Agent Card

Every A2A server exposes an Agent Card at `GET /.well-known/agent.json`:

```json
{
  "name": "Research Agent (OpenAI Agents SDK)",
  "description": "A research specialist...",
  "url": "http://localhost:8001",
  "version": "1.0.0",
  "protocolVersion": "0.2.5",
  "provider": {
    "organization": "Cross-Framework Network Demo",
    "url": "https://github.com/..."
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "skills": [
    {
      "id": "research",
      "name": "Research Briefing",
      "description": "Produces a structured research briefing...",
      "tags": ["research", "analysis"],
      "examples": ["Research the current state of..."]
    }
  ],
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"]
}
```

Clients fetch this card to discover what an agent can do before sending tasks.

## JSON-RPC 2.0 Methods

### `tasks/send` — Send a task (synchronous)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Research multi-agent systems"}]
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "result": {
    "id": "task-uuid",
    "contextId": "context-uuid",
    "status": {"state": "completed", "timestamp": "..."},
    "history": [...],
    "artifacts": [
      {
        "artifactId": "...",
        "name": "result",
        "parts": [{"type": "text", "text": "## Research Findings..."}]
      }
    ]
  }
}
```

### `tasks/get` — Retrieve task status

```json
{"jsonrpc": "2.0", "id": "2", "method": "tasks/get", "params": {"id": "task-uuid"}}
```

### `tasks/cancel` — Cancel a task

```json
{"jsonrpc": "2.0", "id": "3", "method": "tasks/cancel", "params": {"id": "task-uuid"}}
```

### `tasks/list` — List all tasks

```json
{"jsonrpc": "2.0", "id": "4", "method": "tasks/list", "params": {}}
```

### `tasks/sendSubscribe` — Streaming (SSE)

For streaming, the client POSTs to `/tasks/sendSubscribe` and receives Server-Sent Events:

```
POST /tasks/sendSubscribe
Content-Type: application/json

{"jsonrpc": "2.0", "id": "5", "method": "tasks/sendSubscribe", "params": {...}}
```

**Response (SSE):**
```
data: {"id": "task-1", "status": {"state": "working"}, ...}

data: {"id": "task-1", "status": {"state": "completed"}, "artifacts": [...]}
```

## Task Lifecycle

```
    ┌───────────┐
    │ SUBMITTED │ ← task created by tasks/send
    └─────┬─────┘
          ▼
    ┌───────────┐
    │  WORKING  │ ← agent begins processing
    └─────┬─────┘
          │
    ┌─────┼──────────┐
    ▼     ▼          ▼
┌──────┐ ┌──────┐ ┌────────┐
│COMPL.│ │FAILED│ │CANCELED│
└──────┘ └──────┘ └────────┘
```

| State | Meaning |
|-------|---------|
| `submitted` | Task received, not yet started |
| `working` | Agent is processing |
| `input-required` | Agent needs more input (not used in this impl) |
| `completed` | Task finished successfully, artifacts available |
| `canceled` | Task was canceled by the client |
| `failed` | Task encountered an error |
| `unknown` | State cannot be determined |

## Message Parts

A2A messages contain `parts`, which can be:

### TextPart
```json
{"type": "text", "text": "Hello, agent!", "metadata": null}
```

### DataPart (structured JSON)
```json
{"type": "data", "data": {"key": "value"}, "metadata": null}
```

### FilePart (inline bytes or URI)
```json
{
  "type": "file",
  "file": {"name": "report.pdf", "mimeType": "application/pdf", "bytes": "base64..."}
}
```

## Error Handling

Errors follow JSON-RPC 2.0 conventions:

| Code | Meaning | When |
|------|---------|------|
| -32700 | Parse error | Invalid JSON in request |
| -32600 | Invalid request | Missing `jsonrpc` or `method` |
| -32601 | Method not found | Unknown JSON-RPC method |
| -32602 | Invalid params | Missing required parameters |
| -32603 | Internal error | Unhandled server error |
| -32001 | Task not found | `tasks/get` with unknown ID |
| -32002 | Task not cancelable | Canceling a completed/failed task |
| -32003 | Push notification not supported | `tasks/pushNotification/*` |
| -32004 | Unsupported operation | Method exists but not implemented |

Example error response:
```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "error": {
    "code": -32001,
    "message": "Task 'abc-123' not found"
  }
}
```

## Implementation Details

### Server (`a2a/server.py`)

The `A2AServer` class wraps a `FastAPI` application with:
- **Agent Card route** — `GET /.well-known/agent.json`
- **JSON-RPC route** — `POST /` (handles all methods)
- **SSE route** — `POST /tasks/sendSubscribe`
- **Task manager** — pluggable `TaskManager` interface (default: `InMemoryTaskManager`)

The `InMemoryTaskManager` accepts an `execute` callable that receives a `Task` and returns the updated `Task`. This is how agents plug in their logic.

### Client (`a2a/client.py`)

The `A2AClient` class provides:
- `get_agent_card()` — discover an agent
- `send_task(text)` — send a simple text task
- `send_task(message=...)` — send a structured message
- `send_task_streaming(text)` — async iterator of task updates
- `get_task(id)`, `cancel_task(id)`, `list_tasks()`

It uses `httpx.AsyncClient` for non-blocking HTTP.

### Why implement from scratch?

1. **Educational transparency** — you can see exactly how the protocol works
2. **No external A2A SDK dependency** — fewer things to install
3. **Full control** — easy to extend with custom behavior
4. **Spec compliance** — follows the A2A specification closely

The implementation is compatible with any A2A-compliant client or server, and could be swapped for an official SDK without changing the agent or supervisor code.

## References

- [A2A Protocol Specification](https://google.github.io/A2A/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [Agent Card schema](https://google.github.io/A2A/#/objects?id=agentcard)
