# Project 07 — Real-time Anomaly Monitor

> Difficulty: ⭐⭐⭐⭐  •  Agentic AI Roadmap — canonical "real-time" project
>
> Monitor a streaming data source (logs, metrics, transactions), detect anomalies
> in real time, decide on a response, and execute the response with human oversight
> for high-impact actions.

This repository is a **complete, runnable reference implementation** of the spec
in the [Agentic-AI-Roadmap-with-Notes-and-Projects](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects)
repository (`projects/07-anomaly-monitor`). It exercises **async/streaming
agents**, **real-time decision-making**, and **HITL for high-impact actions**.

---

## ✨ What's inside

| Layer | File(s) | What it does |
|-------|---------|--------------|
| **Stream consumer** | `streaming/` | Pluggable sources: real Kafka (`aiokafka`), synthetic in-process stream, or JSONL file replay |
| **Windowed aggregation** | `aggregation/windower.py` | 1-minute and 5-minute tumbling windows, Redis-backed with in-memory fallback |
| **Anomaly detector** | `detection/` | Ensemble of statistical (z-score + Isolation Forest) and LLM-based detectors, weighted voting |
| **Response agent** | `response/graph.py` | LangGraph 0.2.x async state machine: classify → decide → (HITL review) → execute |
| **Actions** | `response/actions.py` | `AlertAction` (PagerDuty), `ScaleAction` (Kubernetes), `BlockAction` (firewall rule file) |
| **HITL** | `response/hitl.py` | Human approval for high-severity actions, via Slack webhook or interactive CLI |
| **Feedback loop** | `feedback/store.py` | SQLite store for operator feedback (real anomaly / not), used by detector retraining |
| **Observability** | `observability/` | Prometheus counters/histograms + LangSmith tracing |
| **Eval** | `eval/` | Precision/recall/latency rubric + LLM-as-judge for response appropriateness |

---

## 🚀 Quick start (local, no infra)

```bash
# 1. Create a venv and install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. (optional) configure LLM. Without an API key, the LLM detector is
#    replaced by a deterministic rule-based stub so the pipeline still runs.
cp .env.example .env
#   edit .env -> set OPENAI_API_KEY=sk-... if you want real LLM calls

# 3. Run the end-to-end pipeline against a synthetic stream
make run-local
#   or:  ANOMON_MODE=local python -m anomaly_monitor.cli run
```

You should see a Rich-rendered console with events flowing through the pipeline,
anomalies being detected, the response agent classifying them, and (for
high-severity cases) a CLI prompt asking you to approve the action.

To seed a 1-hour synthetic dataset for offline eval:

```bash
make seed                       # writes data/generated/synthetic_1h.jsonl
make eval                       # runs the eval rubric against labeled samples
```

---

## 🐳 Running against real Kafka + Redis

```bash
make docker-up                  # Kafka + Redis + Prometheus + Grafana
make run-kafka                  # ANOMON_MODE=kafka
make docker-down
```

The Kafka topic is auto-created. To publish real events into the topic from a
JSONL file:

```bash
python -m anomaly_monitor.cli publish --file data/samples/anomalous.jsonl
```

---

## 🧪 Tests

```bash
make test                       # unit tests, no external deps
make test-integration           # requires Kafka/Redis/OpenAI
```

Coverage focuses on the windower (correct bucketing + expiry), detectors
(z-score + Isolation Forest behaviour, LLM stub fallback), the response graph
(routing, HITL gating), and the end-to-end pipeline (synthetic mode).

---

## 📊 Eval rubric

Implemented in `eval/rubric.py`. Targets match the README:

| Metric | Target | How measured |
|--------|--------|--------------|
| Detection precision | ≥ 80% | `flagged anomalies that are real` |
| Detection recall | ≥ 90% | `real anomalies that are flagged` |
| Response correctness | ≥ 85% | LLM-as-judge on response appropriateness |
| End-to-end latency | < 30s | `anomaly.ts → response.ts` |
| False-positive cost | tracked | business metric, not gated |

Run with `make eval` or `python -m eval.run_eval --data <jsonl> --labels <labels>`.

---

## 🗂 Project layout

```
anomaly-monitor/
├── README.md
├── architecture.md            # design deep-dive
├── pyproject.toml
├── requirements.txt
├── .env.example
├── docker-compose.yml         # Kafka + Redis + Prometheus + Grafana
├── Makefile
├── docs/                      # architecture, deployment, evaluation
├── observability/prometheus.yml
├── src/anomaly_monitor/
│   ├── config.py              # pydantic-settings
│   ├── models.py              # Event / Window / Anomaly / Response / Feedback
│   ├── pipeline.py            # end-to-end async pipeline
│   ├── cli.py                 # `anomaly-monitor` Typer CLI
│   ├── streaming/             # base, kafka, synthetic, file sources
│   ├── aggregation/           # windower (Redis + in-memory)
│   ├── detection/             # statistical + LLM + ensemble
│   ├── response/              # LangGraph state graph + actions + HITL
│   ├── feedback/              # SQLite feedback store
│   └── observability/         # Prometheus + LangSmith
├── data/
│   ├── generator.py           # synthetic 1h log generator with injected anomalies
│   └── samples/               # normal.jsonl, anomalous.jsonl, labels.jsonl
├── eval/
│   ├── rubric.py
│   ├── judge.py
│   └── run_eval.py
├── tests/                     # pytest, asyncio_mode=auto
├── scripts/                   # run_local.sh, run_kafka.sh, seed_data.py
└── notebooks/
```

---

## 🔧 Configuration

All configuration is via environment variables (see `.env.example`). Key ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANOMON_MODE` | `local` | `local` (synthetic) or `kafka` (real) |
| `OPENAI_API_KEY` | _(empty)_ | If empty, LLM detector falls back to a rule-based stub |
| `ANOMON_ZSCORE_THRESHOLD` | `3.0` | Statistical detector threshold |
| `ANOMON_ENSEMBLE_THRESHOLD` | `0.5` | Combined anomaly probability cutoff |
| `ANOMON_HITL_MIN_SEVERITY` | `high` | Actions at/above this severity require human approval |
| `ANOMON_HITL_BACKEND` | `cli` | `cli` or `slack` |
| `LANGSMITH_API_KEY` | _(empty)_ | Enables LangSmith tracing |

---

## 📚 References

- [Datadog Watchdog](https://www.datadoghq.com/auto-detection/) — production reference
- [LangGraph async docs](https://langchain-ai.github.io/langgraph/)
- Original spec: [`projects/07-anomaly-monitor/README.md`](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects/tree/main/projects/07-anomaly-monitor)

---

## License

MIT. Built as a learning reference for the Agentic AI Roadmap.
