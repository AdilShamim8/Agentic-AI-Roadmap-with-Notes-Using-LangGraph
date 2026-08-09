# Evaluation

This guide explains how to generate labeled data, run the evaluation CLI,
interpret the rubric output, and add new labeled datasets.

## Table of Contents

- [Overview](#overview)
- [Generating Labeled Data](#generating-labeled-data)
- [Running the Eval CLI](#running-the-eval-cli)
- [Interpreting the Rubric Output](#interpreting-the-rubric-output)
- [Adding New Labeled Datasets](#adding-new-labeled-datasets)
- [Stretch Goals](#stretch-goals)

---

## Overview

The eval system replays a JSONL file of `Event` objects through the pipeline
(windower → detector → response graph) and compares the flagged anomalies
against a labels file. It computes precision, recall, end-to-end latency,
and (optionally) LLM-as-judge response correctness.

The rubric targets (from the project README):

| Metric                | Target  | How measured                              |
|-----------------------|---------|-------------------------------------------|
| Detection precision   | >= 80%  | flagged anomalies that are real           |
| Detection recall      | >= 90%  | real anomalies that are flagged           |
| Response correctness  | >= 85%  | LLM-as-judge on response appropriateness  |
| End-to-end latency    | < 30s   | anomaly.ts -> response.ts                 |
| False-positive cost   | tracked | business metric, not gated                |

---

## Generating Labeled Data

The `data/generator.py` module produces synthetic log data with injected
anomalies (rate spikes, error bursts, unusual sources, latency regressions).
It writes two files:

- `events.jsonl` — one `Event` JSON per line, in chronological order.
- `labels.jsonl` — one label per line: `{"anomaly_id", "start_ts", "end_ts", "kind"}`.

### Quick Start

```bash
# Generate 1 hour of data at 5 events/sec with 2% anomaly rate
python -m data.generator \
    --hours 1.0 \
    --rate 5 \
    --anomaly-rate 0.02 \
    --out data/generated/synthetic_1h.jsonl \
    --labels data/generated/labels_1h.jsonl \
    --seed 42
```

Or use the convenience script:

```bash
./scripts/seed_data.sh
```

### Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--hours` | `1.0` | Duration of the generated data in hours. |
| `--rate` | `5.0` | Baseline events per second (Poisson arrivals). |
| `--anomaly-rate` | `0.02` | Fraction of events that should be anomalous. |
| `--out` | `data/generated/synthetic.jsonl` | Output events JSONL path. |
| `--labels` | `data/generated/labels.jsonl` | Output labels JSONL path. |
| `--seed` | `42` | RNG seed for reproducibility. |

### Anomaly Types

The generator injects four kinds of anomalies:

1. **`rate_spike`** — 5-30s burst at 10x the baseline rate from a single host.
2. **`error_burst`** — 5-30s burst of `severity=error` / `status_code=500` events.
3. **`unusual_source`** — events from a host not in the normal pool.
4. **`latency_regression`** — events with 5-20x normal latency.

Each anomaly burst is recorded in the labels file with its time window
and kind, so the rubric can match flagged windows to ground truth.

### Sample Data

The repository ships with a small sample dataset:

```bash
# ~30 events with 5 injected anomalies (fast for quick eval runs)
data/samples/anomalous.jsonl
data/samples/labels.jsonl
```

---

## Running the Eval CLI

```bash
python -m eval.run_eval \
    --data data/samples/anomalous.jsonl \
    --labels data/samples/labels.jsonl \
    --speed 100 \
    --out ./.runtime/eval_result.json
```

### Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--data` | _(required)_ | JSONL file of `Event` objects to replay. |
| `--labels` | _(required)_ | JSONL labels file (anomaly_id / start_ts / end_ts / kind). |
| `--out` | `./.runtime/eval_result.json` | Where to write the JSON result. |
| `--speed` | `100.0` | Replay speed multiplier (100 = 100x real-time). |
| `--no-judge` | _(flag)_ | Skip the LLM-as-judge step (response_correctness defaults to 1.0). |

### How It Works

1. The `FileSource` replays the JSONL data file, pacing events by their
   `ts` deltas divided by `--speed`.
2. The in-memory `Windower` builds 1m and 5m tumbling windows (no Redis needed).
3. The `EnsembleDetector` (statistical + LLM-stub) scores each unique window.
4. Flagged anomalies are fed through the `ResponseGraph` with an
   **auto-approving** HITL manager (so the eval never blocks on a human).
5. Each flagged anomaly becomes a `PipelineRecord`.
6. The `ResponseJudge` (LLM-as-judge) optionally grades each record's
   response appropriateness.
7. The `EvalRubric` computes precision / recall / latency / correctness
   and prints a rich table + writes JSON to `--out`.

### Exit Code

The CLI exits `0` if all gated metrics pass (precision, recall, response
correctness, P95 latency), `1` otherwise. This makes it suitable for CI:

```bash
python -m eval.run_eval --data ... --labels ... || exit 1
```

### Using a Real LLM

By default (no `OPENAI_API_KEY`), the LLM detector uses a rule-based stub
and the judge is skipped. To use a real LLM:

```bash
export OPENAI_API_KEY=sk-...
python -m eval.run_eval --data data/samples/anomalous.jsonl --labels data/samples/labels.jsonl
```

This activates both the LLM detector and the LLM-as-judge.

---

## Interpreting the Rubric Output

The CLI prints a rich-formatted table:

```
┌─────────────────────────────────── Anomaly Monitor — Eval Result ───────────────────────────────────┐
│  Metric               Value       Target       Pass   │
│  Precision             83.3%      >= 80%       ✓      │
│  Recall                100.0%     >= 90%       ✓      │
│  Response correctness  100.0%     >= 85%      ✓      │
│  P95 latency           0.15s      < 30s        ✓      │
│  P99 latency           0.18s      (tracked)   —      │
│  FP cost               $10.00     (tracked)   —      │
│  Flagged (TP+FP)       6                       │
│    TP                  5                       │
│    FP                  1                       │
│  Real anomalies        5                       │
│    FN                  0                       │
└────────────────────────────────────────────────────────┘
```

### Metric Definitions

- **Precision** = TP / (TP + FP). Of all flagged anomalies, what fraction
  overlapped a labeled anomaly? (1.0 when nothing is flagged.)
- **Recall** = (n_real - FN) / n_real. Of all labeled anomalies, what
  fraction was overlapped by at least one flagged window? (1.0 when there
  are no labels.)
- **Response correctness** — mean LLM-as-judge score across all flagged
  records. Defaults to 1.0 when `--no-judge` is used or no records exist.
- **P95 / P99 latency** — percentiles of `response_ts - detect_ts` across
  all flagged records.
- **FP cost** — `n_false_positives * $10` (placeholder; replace with a
  real cost model for your business).
- **TP** — flagged record whose window overlaps at least one label.
- **FP** — flagged record whose window overlaps no label.
- **FN** — label not overlapped by any flagged record.

### Matching Rule

A flagged record (window) is a **true positive** iff its time range
`[window.start_ts, window.end_ts]` overlaps a label's
`[label.start_ts, label.end_ts]`. This is **time-overlap matching**, not
one-to-one matching — a single flagged record can cover multiple labels
(counted as 1 TP), and a single label can be covered by multiple records
(counted once for recall).

### JSON Output

The `--out` file contains the same data in JSON format:

```json
{
  "precision": 0.833,
  "recall": 1.0,
  "response_correctness": 1.0,
  "p95_latency_sec": 0.15,
  "p99_latency_sec": 0.18,
  "fp_cost": 10.0,
  "n_flagged": 6,
  "n_real": 5,
  "n_true_positives": 5,
  "n_false_positives": 1,
  "n_false_negatives": 0,
  "passed": {
    "precision": true,
    "recall": true,
    "response_correctness": true,
    "latency_p95": true
  },
  "notes": ["No LLM-as-judge results supplied — response_correctness defaulted to 1.0."]
}
```

---

## Adding New Labeled Datasets

### Format

**Events file** — one JSON `Event` per line:

```json
{"id":"evt_abc123","ts":1700000000.5,"source":"host-1","event_type":"http_request","severity":"info","message":"GET /api/users","features":{"latency_ms":45.2,"bytes":1024,"status_code":200},"is_anomaly":false,"anomaly_kind":null}
```

**Labels file** — one JSON object per line:

```json
{"anomaly_id":"anom-001","start_ts":1700000000.0,"end_ts":1700000005.0,"kind":"rate_spike"}
```

### Steps

1. **Generate or collect** your events data. Use `data/generator.py` for
   synthetic data, or export from your production log pipeline.

2. **Create labels**. For each anomalous time window, add a line to the
   labels file with:
   - `anomaly_id` — unique identifier.
   - `start_ts` / `end_ts` — Unix timestamps of the anomaly window.
   - `kind` — one of `rate_spike`, `error_burst`, `unusual_source`,
     `latency_regression`, or a custom kind.

3. **Place files** under `data/`:

   ```
   data/
     custom/
       my_events.jsonl
       my_labels.jsonl
   ```

4. **Run the eval**:

   ```bash
   python -m eval.run_eval \
       --data data/custom/my_events.jsonl \
       --labels data/custom/my_labels.jsonl \
       --out ./.runtime/eval_custom.json
   ```

### Converting Production Logs

If your production logs are in a different format, write a converter script
that maps each log line to the `Event` schema:

```python
from anomaly_monitor.models import Event

def convert(raw_line: dict) -> Event:
    return Event(
        ts=raw_line["timestamp"],
        source=raw_line["hostname"],
        event_type=raw_line["service"],
        severity=raw_line["level"].lower(),
        message=raw_line["message"],
        features={
            "latency_ms": raw_line.get("duration_ms", 0),
            "status_code": raw_line.get("status", 200),
        },
    )
```

---

## Stretch Goals

### Operator Feedback Learning

The feedback store (`feedback/store.py`) records operator verdicts on whether
a flagged anomaly was real and whether the response action was correct.
Future work: feed this data back into the detector to adjust thresholds.

**Proposed approach:**

1. At startup, load recent feedback from the SQLite store.
2. Compute the false-positive rate per anomaly kind.
3. If a kind has > 30% false positives, raise its `zscore_threshold` by 0.5
   for the next detection cycle.
4. Re-evaluate quarterly using the eval CLI to verify the adjustment
   improved precision without hurting recall.

```python
# Pseudocode — not yet implemented
async def adjust_thresholds_from_feedback(store: FeedbackStore, detector: StatisticalDetector):
    stats = await store.stats()
    fp_rate = 1.0 - stats["real_pct"]
    if fp_rate > 0.30:
        detector._settings.zscore_threshold += 0.5
        log.info("threshold_adjusted", new_value=detector._settings.zscore_threshold)
```

### Concept Drift Detection

Over time, the statistical baseline may drift (e.g., traffic grows naturally).
Future work: detect when the baseline mean shifts significantly and
auto-retrain the Isolation Forest.

**Proposed approach:**

1. Track the rolling mean of `window.count` over the last 100 windows.
2. If the current mean differs from the 1-hour-ago mean by > 2 sigma,
   flag "concept drift" and reset the baseline buffers.
3. Log a warning and emit a Prometheus metric
   (`anomaly_concept_drift_events_total`).

```python
# Pseudocode — not yet implemented
def detect_drift(baseline: list[float], window_size: int = 100) -> bool:
    if len(baseline) < window_size * 2:
        return False
    recent = baseline[-window_size:]
    older = baseline[-window_size * 2:-window_size]
    import numpy as np
    z = abs(np.mean(recent) - np.mean(older)) / max(np.std(older), 1e-6)
    return z > 2.0
```

### Continuous Eval in CI

Wire the eval CLI into CI to catch regressions:

```yaml
# .github/workflows/eval.yml
name: Eval
on: [pull_request]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: python -m data.generator --hours 0.1 --out data/ci.jsonl --labels data/ci_labels.jsonl
      - run: python -m eval.run_eval --data data/ci.jsonl --labels data/ci_labels.jsonl --no-judge
```

The eval CLI exits non-zero if any gated metric fails, blocking the PR.
