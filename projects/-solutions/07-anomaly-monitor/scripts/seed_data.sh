#!/usr/bin/env bash
# =============================================================================
# seed_data.sh — generate 1 hour of synthetic log data for eval / replay.
#
# Produces two files under data/generated/:
#   synthetic_1h.jsonl  — ~18,000 events with injected anomalies
#   labels_1h.jsonl     — ground-truth anomaly windows
#
# Usage:
#   ./scripts/seed_data.sh                    # 1 hour, 5 ev/s, 2% anomalies
#   ./scripts/seed_data.sh --hours 2 --rate 10
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ Generating 1 hour of synthetic data (5 ev/s, 2% anomaly rate, seed=42)..."
echo "   Output: data/generated/synthetic_1h.jsonl + data/generated/labels_1h.jsonl"
echo ""

# Pass through any extra args (e.g. --hours, --rate, --anomaly-rate, --seed)
# while keeping the standard defaults for a 1-hour dataset.
exec python -m data.generator \
    --hours 1.0 \
    --rate 5 \
    --anomaly-rate 0.02 \
    --seed 42 \
    --out data/generated/synthetic_1h.jsonl \
    --labels data/generated/labels_1h.jsonl \
    "$@"
