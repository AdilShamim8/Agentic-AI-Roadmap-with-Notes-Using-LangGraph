# Deployment

This guide covers three deployment scenarios for the anomaly-monitor, from
zero-infrastructure local development to production Kubernetes.

## Table of Contents

- [Local Dev Mode (no infra)](#local-dev-mode-no-infra)
- [Docker Compose (Kafka + Redis + Prometheus + Grafana)](#docker-compose-kafka--redis--prometheus--grafana)
- [Production Considerations](#production-considerations)
- [Environment Variable Reference](#environment-variable-reference)

---

## Local Dev Mode (no infra)

The simplest way to run the pipeline — no Kafka, Redis, or OpenAI required.
The synthetic stream source generates Poisson-arriving events, the windower
uses in-memory dicts, and the LLM detector falls back to a deterministic
rule-based stub.

### Prerequisites

- Python 3.10+
- `pip` (or `uv` / `poetry`)

### Steps

```bash
# 1. Clone and install (editable)
git clone <repo-url> anomaly-monitor
cd anomaly-monitor
python -m pip install -e ".[dev]"

# 2. Run the pipeline in local mode
ANOMON_MODE=local python -m anomaly_monitor.cli run

# Or use the convenience script:
./scripts/run_local.sh
```

The pipeline will:
- Generate synthetic events at 5 events/sec (configurable).
- Build 1-minute and 5-minute tumbling windows in memory.
- Run the statistical + LLM-stub ensemble detector on each window.
- Execute the LangGraph response agent (HITL via CLI prompt for high-severity
  actions).
- Expose Prometheus metrics on port 9001 (or `ANOMON_PROMETHEUS_PORT`).
- Persist operator feedback to `./.runtime/feedback.db` (SQLite).

### Stopping

Press `Ctrl+C`. The pipeline catches `KeyboardInterrupt`, calls `stop()` on
all components, and exits cleanly.

### Running the test suite

```bash
python -m pytest tests/ -v
```

All tests are hermetic — no external services required.

---

## Docker Compose (Kafka + Redis + Prometheus + Grafana)

For a production-like local environment with real Kafka and Redis, use the
provided `docker-compose.yml`.

### Prerequisites

- Docker Engine 24+
- Docker Compose v2

### Steps

```bash
# 1. Start the infrastructure stack
docker compose up -d

# This brings up:
#   - Zookeeper  (port 2181)
#   - Kafka      (port 9092)
#   - Redis      (port 6379)
#   - Prometheus (port 9090)
#   - Grafana    (port 3000, admin/admin)

# 2. Verify services are healthy
docker compose ps

# 3. (Optional) Seed Kafka with sample data
./scripts/publish_to_kafka.sh data/samples/anomalous.jsonl

# 4. Run the pipeline in Kafka mode
ANOMON_MODE=kafka python -m anomaly_monitor.cli run

# Or use the convenience script:
./scripts/run_kafka.sh
```

### Grafana Dashboard

1. Open `http://localhost:3000` (admin / admin).
2. Add Prometheus as a data source: `http://prometheus:9090`.
3. Import a dashboard or build one using these metrics:
   - `anomaly_events_processed_total`
   - `anomaly_windows_total{window="1m"|"5m"}`
   - `anomaly_detected_total{kind,severity}`
   - `anomaly_response_latency_seconds` (histogram)
   - `anomaly_hitl_decisions_total{decision}`
   - `anomaly_consumer_lag_seconds`

### Teardown

```bash
docker compose down          # stop containers
docker compose down -v       # also remove volumes
```

---

## Production Considerations

### Kubernetes

The pipeline is designed to run as a long-lived `Deployment` in Kubernetes.
A minimal manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anomaly-monitor
  labels:
    app: anomaly-monitor
spec:
  replicas: 1            # scale horizontally with partitioned consumer groups
  selector:
    matchLabels:
      app: anomaly-monitor
  template:
    metadata:
      labels:
        app: anomaly-monitor
    spec:
      containers:
        - name: anomaly-monitor
          image: ghcr.io/<org>/anomaly-monitor:latest
          command: ["python", "-m", "anomaly_monitor.cli", "run", "--mode", "kafka"]
          envFrom:
            - secretRef:
                name: anomaly-monitor-secrets
            - configMapRef:
                name: anomaly-monitor-config
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /metrics
              port: 9001
            initialDelaySeconds: 30
            periodSeconds: 30
```

### Secrets Management

Store sensitive values in Kubernetes Secrets (never in ConfigMaps or images):

```bash
kubectl create secret generic anomaly-monitor-secrets \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=PAGERDUTY_API_KEY=... \
  --from-literal=K8S_TOKEN=... \
  --from-literal=SLACK_WEBHOOK_URL=https://hooks.slack.com/... \
  --from-literal=LANGSMITH_API_KEY=lsv2_...
```

Non-sensitive configuration goes in a ConfigMap:

```bash
kubectl create configmap anomaly-monitor-config \
  --from-literal=ANOMON_MODE=kafka \
  --from-literal=KAFKA_BOOTSTRAP_servers=kafka:9092 \
  --from-literal=REDIS_URL=redis://redis:6379/0 \
  --from-literal=ANOMON_HITL_BACKEND=slack \
  --from-literal=PROMETHEUS_PORT=9001
```

### Scaling

| Dimension | Strategy |
|-----------|----------|
| **Throughput** | Increase `replicas` and assign each pod a different `KAFKA_CONSUMER_GROUP` or rely on Kafka partition rebalancing (one consumer per partition). |
| **Window memory** | Increase Redis memory; the windower uses sorted sets with TTLs so old windows auto-expire. |
| **LLM latency** | The ensemble runs the statistical and LLM detectors concurrently (`asyncio.gather`). To reduce latency, lower `ANOMON_LLM_TIMEOUT_SEC` or use a faster model. |
| **HITL bottleneck** | Switch from CLI to Slack backend (`ANOMON_HITL_BACKEND=slack`) so multiple operators can approve in parallel. |

### High Availability

- **Kafka**: use a 3+ broker cluster with `min.insync.replicas=2`.
- **Redis**: use Redis Sentinel or Redis Cluster for failover.
- **Pipeline pods**: run 2+ replicas with different consumer group offsets
  so a pod crash doesn't lose detection coverage.
- **Feedback DB**: SQLite is fine for single-pod deployments. For HA,
  switch to PostgreSQL by changing the `feedback_db` connection string
  (SQLAlchemy supports it; add `asyncpg` to dependencies).

### Monitoring the Monitor

The pipeline exports its own Prometheus metrics on `ANOMON_PROMETHEUS_PORT`.
Key alerts to configure:

| Alert | Expression | Severity |
|-------|------------|----------|
| Pipeline down | `anomaly_pipeline_running == 0` | critical |
| High consumer lag | `anomaly_consumer_lag_seconds > 60` | warning |
| No events processed | `rate(anomaly_events_processed_total[5m]) == 0` | critical |
| High anomaly rate | `rate(anomaly_detected_total[5m]) > 10` | warning |
| HITL denials | `rate(anomaly_hitl_decisions_total{decision="denied"}[1h]) > 5` | info |

---

## Environment Variable Reference

All variables are optional with sensible defaults. See [`.env.example`](../.env.example)
for the full list with comments. Variables use no prefix (the project was
originally `ANOMON_`-prefixed; both forms work via `case_sensitive=False`).

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `ANOMON_MODE` | `local` | `local` (synthetic) or `kafka` (real stream). |
| `ANOMON_LOG_LEVEL` | `INFO` | structlog / Python logging level. |

### LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | _(empty)_ | If empty, LLM detector uses a rule-based stub. |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Override for Azure / local LLMs. |
| `ANOMON_LLM_MODEL` | `gpt-4o-mini` | Model name. |
| `ANOMON_LLM_TEMPERATURE` | `0.0` | Sampling temperature (0 = deterministic). |
| `ANOMON_LLM_TIMEOUT_SEC` | `20` | Per-call timeout. |

### Streaming (Kafka)

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker addresses. |
| `KAFKA_TOPIC` | `anomaly.events` | Topic to consume from. |
| `KAFKA_CONSUMER_GROUP` | `anomaly-monitor` | Consumer group ID. |
| `KAFKA_AUTO_OFFSET_RESET` | `earliest` | `earliest` or `latest`. |

### State (Redis)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL. |
| `ANOMON_WINDOW_TTL_SEC` | `3600` | Window expiry in seconds. |

### Windowing

| Variable | Default | Description |
|----------|---------|-------------|
| `ANOMON_WINDOW_1M_SEC` | `60` | Short window duration. |
| `ANOMON_WINDOW_5M_SEC` | `300` | Long window duration. |

### Detection

| Variable | Default | Description |
|----------|---------|-------------|
| `ANOMON_ZSCORE_THRESHOLD` | `3.0` | Z-score above which a window is flagged. |
| `ANOMON_ISOLATION_CONTAMINATION` | `0.05` | Isolation Forest contamination ratio. |
| `ANOMON_LLM_WEIGHT` | `0.6` | LLM weight in the ensemble. |
| `ANOMON_STAT_WEIGHT` | `0.4` | Statistical weight in the ensemble. |
| `ANOMON_ENSEMBLE_THRESHOLD` | `0.5` | Combined probability above which `is_anomaly=True`. |

### Response Policy

| Variable | Default | Description |
|----------|---------|-------------|
| `ANOMON_HITL_MIN_SEVERITY` | `high` | Actions at or above this severity require HITL. |
| `ANOMON_HITL_BACKEND` | `cli` | `cli` or `slack`. |
| `SLACK_WEBHOOK_URL` | _(empty)_ | Slack incoming webhook for HITL. |

### Alerting / Scaling / Blocking

| Variable | Default | Description |
|----------|---------|-------------|
| `PAGERDUTY_API_KEY` | _(empty)_ | PagerDuty Events API v2 routing key. |
| `PAGERDUTY_SERVICE_ID` | _(empty)_ | Default alert target. |
| `K8S_API_URL` | _(empty)_ | Kubernetes API server URL. |
| `K8S_NAMESPACE` | `default` | K8s namespace for ScaleAction. |
| `K8S_DEPLOYMENT` | `anomaly-target` | Default deployment to scale. |
| `K8S_TOKEN` | _(empty)_ | Bearer token for K8s API. |
| `FIREWALL_RULES_FILE` | `./.runtime/firewall_rules.jsonl` | JSONL file for BlockAction rules. |

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGSMITH_API_KEY` | _(empty)_ | If set, enables LangSmith tracing. |
| `LANGSMITH_PROJECT` | `anomaly-monitor` | LangSmith project name. |
| `PROMETHEUS_PORT` | `9001` | Prometheus metrics HTTP port. |
| `ANOMON_FEEDBACK_DB` | `./.runtime/feedback.db` | SQLite path for feedback store. |

### Synthetic Source

| Variable | Default | Description |
|----------|---------|-------------|
| `ANOMON_SYNTHETIC_EVENTS_PER_SEC` | `5.0` | Event generation rate (local mode). |
| `ANOMON_SYNTHETIC_ANOMALY_RATE` | `0.02` | Fraction of events that are anomalous. |
