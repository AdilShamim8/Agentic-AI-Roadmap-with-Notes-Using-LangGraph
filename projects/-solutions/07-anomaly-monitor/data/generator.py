"""Synthetic log-data generator with injected anomalies.

Generates ``hours`` of synthetic :class:`~anomaly_monitor.models.Event` data
with realistic features (``latency_ms`` log-normal around 50ms, ``bytes``
uniform 100-5000, ``status_code`` weighted 200/404/500) and injects
burst-style anomalies (rate spikes, error bursts, unusual sources, latency
regressions). Writes one Event JSON per line to an output JSONL file, plus a
sidecar ``labels.jsonl`` describing each injected burst as::

    {"anomaly_id": "anom-001", "start_ts": <float>, "end_ts": <float>, "kind": "rate_spike"}

Runnable as ``python -m data.generator --hours 1.0 --rate 5``.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_HOSTS = [f"host-{i}" for i in range(1, 6)]
_EVENT_TYPES = ["http_request", "db_query", "cache_lookup", "background_job"]
# Weighted severities: info 80%, warning 18%, error 2%.
_SEVERITY_POOL = ["info"] * 80 + ["warning"] * 18 + ["error"] * 2
# Weighted status codes: 200 dominant, 404 moderate, 500 rare.
_STATUS_POOL = [200] * 85 + [404] * 10 + [500] * 5
_ANOMALY_KINDS = ["rate_spike", "error_burst", "unusual_source", "latency_regression"]
_MESSAGES = {
    "http_request": ["GET /api/users", "POST /api/orders", "GET /health", "PUT /api/cart"],
    "db_query": ["SELECT * FROM orders", "INSERT INTO events", "UPDATE users SET last_seen=now()"],
    "cache_lookup": ["cache hit", "cache miss", "cache eviction"],
    "background_job": ["job completed", "job started", "cleanup ran"],
}


@dataclass
class Burst:
    """A scheduled anomaly burst over ``[start_ts, end_ts)``."""

    anomaly_id: str
    start_ts: float
    end_ts: float
    kind: str
    host: Optional[str] = None  # fixed host for rate_spike / unusual_source


def _make_event(
    ts: float, source: str, event_type: str, severity: str, message: str,
    latency_ms: float, bytes_val: int, status_code: int,
    is_anomaly: bool = False, anomaly_kind: Optional[str] = None,
) -> dict[str, Any]:
    """Build an Event-shaped dict ready to be JSON-serialised to JSONL."""
    return {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "ts": ts,
        "source": source,
        "event_type": event_type,
        "severity": severity,
        "message": message,
        "features": {
            "latency_ms": float(latency_ms),
            "bytes": float(bytes_val),
            "status_code": float(status_code),
        },
        "is_anomaly": is_anomaly,
        "anomaly_kind": anomaly_kind,
    }


def _normal_event(rng: random.Random, ts: float, source: Optional[str] = None) -> dict[str, Any]:
    """Generate a typical, non-anomalous event."""
    event_type = rng.choice(_EVENT_TYPES)
    # log-normal around 50ms (median = 50, sigma controls spread).
    latency = rng.lognormvariate(mu=math.log(50.0), sigma=0.4)
    return _make_event(
        ts=ts,
        source=source or rng.choice(_HOSTS),
        event_type=event_type,
        severity=rng.choice(_SEVERITY_POOL),
        message=rng.choice(_MESSAGES[event_type]),
        latency_ms=latency,
        bytes_val=rng.randint(100, 5000),
        status_code=rng.choice(_STATUS_POOL),
    )


def _anomaly_event(rng: random.Random, burst: Burst, ts: float) -> dict[str, Any]:
    """Generate one event that is part of the given anomaly burst."""
    if burst.kind == "rate_spike":
        # All burst events come from the same host; otherwise normal features.
        ev = _normal_event(rng, ts, source=burst.host or rng.choice(_HOSTS))
    elif burst.kind == "error_burst":
        ev = _normal_event(rng, ts)
        ev["severity"] = "error"
        ev["message"] = "upstream timeout"
        ev["features"]["status_code"] = 500.0
    elif burst.kind == "unusual_source":
        ev = _normal_event(rng, ts, source=burst.host or "host-anomalous-0")
        ev["message"] = "unexpected source connection"
    elif burst.kind == "latency_regression":
        ev = _normal_event(rng, ts)
        ev["features"]["latency_ms"] = ev["features"]["latency_ms"] * rng.uniform(5.0, 20.0)
        ev["message"] = "slow query detected"
    else:  # defensive — unknown kind falls back to a normal event
        ev = _normal_event(rng, ts)
    ev["is_anomaly"] = True
    ev["anomaly_kind"] = burst.kind
    return ev


def _schedule_bursts(
    rng: random.Random, start_ts: float, end_ts: float,
    rate: float, anomaly_rate: float,
) -> list[Burst]:
    """Schedule non-overlapping anomaly bursts covering ~anomaly_rate of events.

    Each burst lasts 5-30s. ``rate_spike`` bursts run at 10x baseline rate;
    others at baseline. Bursts are placed at random start times and rejected
    if they overlap an already-scheduled burst (after 20 retries, give up).
    """
    duration = end_ts - start_ts
    target_anom = rate * duration * anomaly_rate
    bursts: list[Burst] = []
    cumulative_anom = 0.0
    n_burst = 0        # monotonically-increasing burst id (anom-001, anom-002, ...)
    n_unusual = 0      # separate counter for unusual-source host names
    while cumulative_anom < target_anom:
        kind = rng.choice(_ANOMALY_KINDS)
        burst_rate = rate * 10.0 if kind == "rate_spike" else rate
        burst_dur = rng.uniform(5.0, 30.0)
        # Soft-cap duration so a single burst (esp. rate_spike) doesn't
        # overshoot the target by more than ~50%. Clamped to the 5s minimum.
        remaining = max(0.0, target_anom * 1.5 - cumulative_anom)
        if burst_rate * burst_dur > remaining and remaining > 0:
            burst_dur = max(5.0, remaining / burst_rate)
        max_start = max(start_ts, end_ts - burst_dur)
        # Find a non-overlapping start time (try up to 20 times).
        bstart: Optional[float] = None
        for _ in range(20):
            cand = rng.uniform(start_ts, max_start)
            cand_end = cand + burst_dur
            if all(cand_end <= b.start_ts or cand >= b.end_ts for b in bursts):
                bstart = cand
                break
        if bstart is None:
            break  # couldn't fit any more bursts — stop scheduling
        bend = bstart + burst_dur
        n_burst += 1
        host: Optional[str] = None
        if kind == "rate_spike":
            host = rng.choice(_HOSTS)
        elif kind == "unusual_source":
            n_unusual += 1
            host = f"host-anomalous-{n_unusual}"
        bursts.append(Burst(
            anomaly_id=f"anom-{n_burst:03d}",
            start_ts=bstart, end_ts=bend, kind=kind, host=host,
        ))
        cumulative_anom += burst_rate * burst_dur
    bursts.sort(key=lambda b: b.start_ts)
    return bursts


def generate(
    hours: float, rate: float, anomaly_rate: float,
    out: Path, labels: Path, seed: int,
) -> tuple[int, int]:
    """Generate synthetic events + labels and write them to disk.

    Returns ``(num_events, num_bursts)``. Events are written in chronological
    order; ``ts`` starts at :func:`time.time` and goes forward.
    """
    rng = random.Random(seed)
    start_ts = time.time()
    end_ts = start_ts + hours * 3600.0
    bursts = _schedule_bursts(rng, start_ts, end_ts, rate, anomaly_rate)

    events: list[dict[str, Any]] = []
    # 1) Normal events via Poisson arrivals (skip ts inside any burst window).
    ts = start_ts
    while ts < end_ts:
        if not any(b.start_ts <= ts < b.end_ts for b in bursts):
            events.append(_normal_event(rng, ts))
        ts += rng.expovariate(rate)
    # 2) Burst events: walk each burst window at the burst rate.
    for b in bursts:
        burst_rate = rate * 10.0 if b.kind == "rate_spike" else rate
        bts = b.start_ts
        while bts < b.end_ts:
            events.append(_anomaly_event(rng, b, bts))
            bts += rng.expovariate(burst_rate)
    # Sort chronologically (Poisson arrivals may interleave bursts).
    events.sort(key=lambda e: e["ts"])

    out.parent.mkdir(parents=True, exist_ok=True)
    labels.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    with labels.open("w") as f:
        for b in bursts:
            f.write(json.dumps({
                "anomaly_id": b.anomaly_id,
                "start_ts": b.start_ts,
                "end_ts": b.end_ts,
                "kind": b.kind,
            }) + "\n")
    return len(events), len(bursts)


def main() -> None:
    """CLI entry point. Parses args and runs :func:`generate`."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic anomaly-monitor log data (JSONL).",
    )
    parser.add_argument("--hours", type=float, default=1.0, help="Duration in hours (default: 1.0).")
    parser.add_argument("--rate", type=float, default=5.0, help="Baseline events/sec (default: 5.0).")
    parser.add_argument("--anomaly-rate", type=float, default=0.02,
                        help="Fraction of events anomalous (default: 0.02).")
    parser.add_argument("--out", type=Path, default=Path("data/generated/synthetic.jsonl"),
                        help="Output JSONL path (default: data/generated/synthetic.jsonl).")
    parser.add_argument("--labels", type=Path, default=Path("data/generated/labels.jsonl"),
                        help="Sidecar labels JSONL path (default: data/generated/labels.jsonl).")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42).")
    args = parser.parse_args()

    n_events, n_bursts = generate(
        hours=args.hours, rate=args.rate, anomaly_rate=args.anomaly_rate,
        out=args.out, labels=args.labels, seed=args.seed,
    )
    print(f"Wrote {n_events} events to {args.out}")
    print(f"Wrote {n_bursts} anomaly bursts to {args.labels}")


if __name__ == "__main__":
    main()
