# Architecture

## Goals

1. **Real-time** — anomaly → response in under 30 seconds (P95).
2. **Pluggable** — swap Kafka for synthetic, Redis for in-memory, OpenAI for a
   rule-based stub, without touching the pipeline glue.
3. **HITL by default** — any action with severity ≥ `ANOMON_HITL_MIN_SEVERITY`
   is held for human approval before execution.
4. **Observable** — every node is traced (LangSmith) and metered (Prometheus).
5. **Evaluable** — the same pipeline can be run in batch mode against labeled
   data to compute precision/recall/latency.

## Data flow

```
┌──────────────┐    events    ┌───────────────┐   windows   ┌──────────────┐
│  Stream      │ ───────────▶ │  Windower     │ ──────────▶ │  Detector    │
│  (Kafka/     │              │  (1m / 5m,    │             │  (z-score +  │
│   synthetic) │              │   Redis)      │             │   IF + LLM)  │
└──────────────┘              └───────────────┘             └──────┬───────┘
                                                                   │ anomaly?
                                                                   ▼
┌──────────────┐   action    ┌───────────────┐   decision  ┌──────────────┐
│  Feedback    │ ◀────────── │  Response     │ ◀────────── │  LangGraph   │
│  store       │             │  actions      │             │  async state │
│  (SQLite)    │             │  (alert/scale/│             │  machine     │
└──────────────┘             │   block)      │             └──────┬───────┘
                             └───────┬───────┘                    │
                                     │ high-severity?              │
                                     ▼                            │
                             ┌───────────────┐                    │
                             │  HITL review  │ ◀──────────────────┘
                             │  (Slack/CLI)  │
                             └───────────────┘
```

## Components

### 1. Stream consumer — `streaming/`

A single async interface (`StreamConsumer`) yields `Event` objects:

```python
class StreamConsumer(abc.ABC):
    async def events(self) -> AsyncIterator[Event]: ...
    async def aclose(self) -> None: ...
```

Three implementations:

- **`KafkaConsumer`** — wraps `aiokafka.AIOKafkaConsumer`, deserializes JSON to
  `Event`. Auto-creates the topic if needed.
- **`SyntheticConsumer`** — generates Poisson-arriving events at a configurable
  rate, with occasional injected anomalies (rate spike, error burst, unusual
  source). Used by `make run-local` and by the test-suite.
- **`FileSource`** — replays a JSONL file in real time (paces events by their
  `ts` field). Used by `make eval`.

### 2. Windower — `aggregation/windower.py`

Tumbling time windows over event counts and error-rates. Backed by Redis
(sorted sets per window key) with a transparent in-memory fallback when Redis
is unreachable or `ANOMON_MODE=local`. Windows have a TTL so old buckets
expire.

Each window exposes:
- `count` — total events
- `error_count` / `error_rate`
- `unique_sources`
- `latency_p50 / p95 / p99`
- `event_types: dict[str, int]`

### 3. Detectors — `detection/`

Three pluggable detectors implementing a common interface:

```python
class Detector(abc.ABC):
    async def detect(self, window: Window) -> AnomalyScore: ...
```

- **`StatisticalDetector`** — z-score over `count` and `error_rate` (computed
  against a rolling baseline of the previous N windows) **plus** an Isolation
  Forest over the multi-dimensional feature vector. The two are combined into a
  single probability.
- **`LLMAnomalyDetector`** — asks the LLM: "Given this window's stats, is this
  anomalous? Return JSON `{is_anomaly, probability, reason}`." Uses
  `langchain_openai.ChatOpenAI`. If `OPENAI_API_KEY` is unset, falls back to a
  deterministic rule-based stub so the pipeline still runs end-to-end.
- **`EnsembleDetector`** — weighted average of the two (configurable weights,
  default 0.6 LLM / 0.4 statistical). Final `is_anomaly` flag when combined
  probability ≥ `ANOMON_ENSEMBLE_THRESHOLD`.

### 4. Response agent — `response/graph.py`

LangGraph `StateGraph` (async), state shape in `response/state.py`:

```python
class ResponseState(TypedDict):
    window: Window
    anomaly: AnomalyScore
    severity: Severity
    proposed_action: Optional[Action]
    approved: Optional[bool]
    executed: bool
    feedback: Optional[Feedback]
    trace: list[str]
```

Nodes:
1. `classify_severity` — maps anomaly probability + kind to `info | warning | high | critical`.
2. `propose_action` — LLM call (or rule) chooses `alert`, `scale`, `block`, or `noop`.
3. `hitl_review` — **conditional edge**: if `severity >= ANOMON_HITL_MIN_SEVERITY`,
   route through HITL; otherwise route directly to execute.
4. `execute_action` — runs the action (with `tenacity` retry).

The graph is compiled with `async_compile()` and streamed via `astream()` so
the pipeline can interleave detection and response without blocking.

### 5. Actions — `response/actions.py`

```python
class Action(abc.ABC):
    severity: Severity
    async def execute(self) -> ActionResult: ...
```

- `AlertAction` — POST to PagerDuty Events API v2 (or a stub that just logs).
- `ScaleAction` — patch a Kubernetes Deployment (or a stub that prints the
  intended replica count).
- `BlockAction` — append a JSONL rule to `FIREWALL_RULES_FILE`.
- `NoopAction` — no-op, for sub-threshold anomalies.

All actions are wrapped in `tenacity.retry` (3 attempts, exponential backoff).

### 6. HITL — `response/hitl.py`

`HITLManager.request_approval(action)` returns a future that resolves to
`True`/`False`/`"modified"`:

- **`cli` backend** — uses `rich` to render an interactive prompt and waits for
  `y/n/m <new action>` from stdin.
- **`slack` backend** — posts a Block Kit message to `SLACK_WEBHOOK_URL` with
  Approve/Deny buttons, then polls a Slack action endpoint (or shortens to a
  fixed timeout and defaults to Deny).

### 7. Feedback loop — `feedback/store.py`

`FeedbackStore` (SQLAlchemy + `aiosqlite`) records:

```python
class Feedback(Base):
    id: int
    anomaly_id: str
    is_real_anomaly: bool
    action_correct: Optional[bool]
    operator_note: Optional[str]
    created_at: datetime
```

The detector reads recent feedback at startup to adjust its baseline
(soft-online-learning: feedback marked "not a real anomaly" lowers the z-score
threshold for similar future windows). Full online retraining is a stretch goal.

### 8. Observability — `observability/`

- `metrics.py` — Prometheus counters/histograms:
  - `anomaly_events_processed_total`
  - `anomaly_windows_total{window="1m"|"5m"}`
  - `anomaly_detected_total{kind}`
  - `anomaly_response_latency_seconds` (histogram)
  - `anomaly_hitl_decisions_total{decision}`
- `tracing.py` — sets `LANGSMITH_TRACING=true` and tags every node with
  `@traceable`. Falls back to no-op if no key.

## Modes

| Mode | Stream | Aggregation | LLM | HITL | Use case |
|------|--------|-------------|-----|------|----------|
| `local` | synthetic | in-memory | stub or real | CLI | dev, tests, demos |
| `kafka` | Kafka | Redis | real | Slack (or CLI) | production-like |
| `eval`  | file | in-memory | real | skipped | offline eval |

## Latency budget

| Stage | Budget |
|-------|--------|
| Consume → window | ≤ 2 s |
| Detect (stat + LLM) | ≤ 10 s |
| Classify + propose | ≤ 5 s |
| HITL (if needed) | ≤ 60 s (not in the 30 s budget — HITL is async) |
| Execute | ≤ 5 s |
| **End-to-end (no HITL)** | **≤ 22 s** (target: < 30 s) |

## Failure modes & mitigations

- **LLM timeout / 5xx** → `tenacity` retry (3×, exp backoff); on final failure
  the LLM detector returns `probability=0.0` with `reason="llm_unavailable"` and
  the ensemble falls back to the statistical score.
- **Redis down** → windower falls back to in-memory with a warning log. The
  pipeline keeps running; accuracy is unaffected for short windows.
- **Kafka consumer lag** → exposed as a Prometheus gauge; the pipeline does
  **not** back-pressure (anomaly detection wins over throughput).
- **HITL timeout** → defaults to Deny (safe by default); the action is logged
  as `denied_timeout`.
