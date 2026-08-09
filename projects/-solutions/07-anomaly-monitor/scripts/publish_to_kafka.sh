#!/usr/bin/env bash
# =============================================================================
# publish_to_kafka.sh — publish events from a JSONL file to the Kafka topic.
#
# Prerequisites:
#   - Kafka running (docker compose up -d)
#   - aiokafka installed (pip install aiokafka)
#
# Usage:
#   ./scripts/publish_to_kafka.sh data/samples/anomalous.jsonl
#   ./scripts/publish_to_kafka.sh data/generated/synthetic_1h.jsonl --topic custom.events
#
# The file must contain one valid JSON Event per line. Lines are validated
# before publishing; invalid JSON lines are skipped with a warning.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <events.jsonl> [--topic <topic_name>]"
    echo ""
    echo "Examples:"
    echo "  $0 data/samples/anomalous.jsonl"
    echo "  $0 data/generated/synthetic_1h.jsonl --topic anomaly.events"
    echo ""
    echo "Make sure Kafka is running:"
    echo "  docker compose up -d"
    exit 1
fi

FILE="$1"
shift || true

if [[ ! -f "$FILE" ]]; then
    echo "✗ File not found: $FILE"
    exit 1
fi

LINES=$(wc -l < "$FILE")
echo "▶ Publishing $LINES events from $FILE to Kafka topic '${KAFKA_TOPIC:-anomaly.events}'..."
echo "   Broker: ${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
echo ""

exec python -m anomaly_monitor.cli publish --file "$FILE" "$@"
