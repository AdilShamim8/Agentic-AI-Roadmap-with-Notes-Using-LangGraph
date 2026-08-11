#!/usr/bin/env bash
# =============================================================================
# Invoke a sample agent end-to-end through the FastAPI backend.
# Usage: ./scripts/invoke-sample.sh "<message>" [skill_id]
# =============================================================================
set -euo pipefail

API="${API:-http://localhost:8000}"
MESSAGE="${1:-What is A2A protocol?}"
SKILL="${2:-researcher}"

echo "==> Logging in as demo user"
RESP=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@a2a.local","password":"demo-pass-123"}')
TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "==> Listing agents"
AGENTS=$(curl -s "$API/agents" -H "Authorization: Bearer $TOKEN")
AGENT_ID=$(echo "$AGENTS" | python3 -c "
import sys, json
agents = json.load(sys.stdin)
print(agents[0]['id'] if agents else '')
")

if [ -z "$AGENT_ID" ]; then
  echo "No agents found. Run ./scripts/seed.sh first."
  exit 1
fi

echo "==> Invoking agent $AGENT_ID with skill=$SKILL"
echo "    Message: $MESSAGE"
echo

curl -s -X POST "$API/agents/$AGENT_ID/invoke" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "import json; print(json.dumps({'message': '$MESSAGE', 'skill_id': '$SKILL'}))")" \
  | python3 -m json.tool
