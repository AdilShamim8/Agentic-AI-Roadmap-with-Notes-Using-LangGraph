#!/usr/bin/env bash
# =============================================================================
# run_kafka.sh — run the anomaly-monitor pipeline in Kafka mode.
#
# Prerequisites:
#   - Docker Compose stack running (Kafka + Redis + Prometheus + Grafana)
#   - Start it with:  docker compose up -d
#
# Usage:
#   ./scripts/run_kafka.sh                  # run forever, consuming from Kafka
#   ./scripts/run_kafka.sh --max-events 500
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

export ANOMON_MODE="${ANOMON_MODE:-kafka}"

# ---------------------------------------------------------------------------
# Check that the docker-compose services are up (best-effort hint).
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    echo "⚠  docker not found on PATH. Kafka mode requires the docker-compose stack."
    echo "   Install Docker, then run:  docker compose up -d"
    exit 1
fi

if ! docker compose ps --services --filter "status=running" 2>/dev/null | grep -q "kafka"; then
    echo "⚠  Kafka service does not appear to be running."
    echo "   Start the stack with:"
    echo "       docker compose up -d"
    echo "   Then verify with:"
    echo "       docker compose ps"
    echo ""
    echo "   Once Kafka is up, re-run this script."
    exit 1
fi

echo "▶ Starting anomaly-monitor in KAFKA mode (consuming from ${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092})..."
exec python -m anomaly_monitor.cli run "$@"
