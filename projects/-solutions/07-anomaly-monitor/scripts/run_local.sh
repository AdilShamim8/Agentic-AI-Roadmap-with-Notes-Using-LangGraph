#!/usr/bin/env bash
# =============================================================================
# run_local.sh — run the anomaly-monitor pipeline in local (synthetic) mode.
#
# No external infrastructure required. Uses an in-memory synthetic event
# source, in-memory windower, and the LLM-stub detector (unless OPENAI_API_KEY
# is set). Ideal for development, demos, and quick smoke tests.
#
# Usage:
#   ./scripts/run_local.sh                  # run forever
#   ./scripts/run_local.sh --max-events 100 # stop after 100 events
#   ANOMON_SYNTHETIC_EVENTS_PER_SEC=20 ./scripts/run_local.sh
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

export ANOMON_MODE="${ANOMON_MODE:-local}"

echo "▶ Starting anomaly-monitor in LOCAL mode (synthetic stream, in-memory)..."
exec python -m anomaly_monitor.cli run "$@"
