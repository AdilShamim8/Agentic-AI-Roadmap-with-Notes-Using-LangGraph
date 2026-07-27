# Project 07 - Real-time anomaly monitor

Difficulty: ⭐⭐⭐⭐
Estimated time: 3-4 weeks
Status: spec

## Problem

Monitor a streaming data source (logs, metrics, transactions), detect anomalies, and trigger automated responses (alert, scale, block). The system must detect anomalies in real time, decide on a response, and execute the response with human oversight for high-impact actions.

This project exercises async/streaming agents, real-time decision-making, and HITL for high-impact actions. It is the canonical "real-time" project.

## Architecture

1. Stream consumer: Kafka or Kinesis consumer that reads events.
2. Windowed aggregation: aggregate events into time windows (1-minute, 5-minute).
3. Anomaly detector: statistical (z-score, isolation forest) + LLM-based (the LLM looks at the window and decides if it is anomalous).
4. Response agent: LangGraph that decides what to do based on the anomaly. Options: alert (PagerDuty), scale (Kubernetes API), block (write a rule to a firewall).
5. Feedback loop: record whether the response was correct (operator feedback), update the detector.

## Stack

- Orchestration: LangGraph 0.2.x (async)
- Streaming: Kafka or Kinesis
- State: Redis (windowed aggregation)
- LLM: GPT-4o or Claude Sonnet
- Observability: LangSmith + Prometheus
- Alerting: PagerDuty
- HITL: Slack approval for high-impact actions

## Eval rubric

| Metric | Target | How measured |
|--------|--------|--------------|
| Detection precision | 80%+ | Flagged anomalies that are real |
| Detection recall | 90%+ | Real anomalies that are flagged |
| Response correctness | 85%+ | LLM-as-judge on response appropriateness |
| End-to-end latency | under 30s | Anomaly to response |
| False-positive cost | tracked | Business metric, not gated |

## Datasets

- 1 hour of synthetic log data with injected anomalies
- 1 hour of real (anonymized) log data
- Hand-labeled anomalies for evaluation

## Stretch goals

- Learn from operator feedback (every "not a real anomaly" response updates the detector)
- Handle concept drift (the definition of anomaly changes over time)
- Multi-source correlation (an anomaly in one stream correlates with an anomaly in another)

## References

- [Datadog's Watchdog](https://www.datadoghq.com/auto-detection/) - production reference
- Real job postings: search "AI engineer" + "anomaly detection" or "observability" on builtin.com

## Solution

Reference solution: [projects/-solutions/07-anomaly-monitor/](-solutions/07-anomaly-monitor/) (coming soon). Build your own first.
