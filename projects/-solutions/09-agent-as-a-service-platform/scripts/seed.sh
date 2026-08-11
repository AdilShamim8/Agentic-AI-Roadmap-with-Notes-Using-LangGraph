#!/usr/bin/env bash
# =============================================================================
# Seed script — registers 5 sample agents in the database via the API.
# Run AFTER `docker compose up` has finished booting.
# =============================================================================
set -euo pipefail

API="${API:-http://localhost:8000}"
GATEWAY="${GATEWAY:-http://localhost:8080}"
SAMPLE_AGENT_URL="${SAMPLE_AGENT_URL:-http://agent-runtime:8081}"

echo "==> Seeding sample agents against $API"

# -----------------------------------------------------------------------------
# 1. Register a demo user and grab a JWT
# -----------------------------------------------------------------------------
echo "  → registering demo user"
RESP=$(curl -s -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@a2a.local","username":"demo","password":"demo-pass-123","full_name":"Demo User"}' \
  || true)

TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
  echo "  → user exists, logging in instead"
  RESP=$(curl -s -X POST "$API/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"demo@a2a.local","password":"demo-pass-123"}')
  TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
fi

echo "  → got token (length=${#TOKEN})"

# -----------------------------------------------------------------------------
# 2. Deploy 5 sample agents (all pointing at the sample runtime image)
# -----------------------------------------------------------------------------
declare -a AGENTS=(
  '{"name":"Research Agent","description":"Answers factual questions about A2A, LangGraph, FastAPI, and Stripe.","version":"1.0.0","docker_image":"a2a-agent-runtime:latest","price_per_invocation_cents":0,"skills":[{"id":"researcher","name":"Researcher","description":"Knowledge-base QA","tags":["research","qa"]}]}'
  '{"name":"Coder Agent","description":"Generates Python snippets for common tasks.","version":"1.0.0","docker_image":"a2a-agent-runtime:latest","price_per_invocation_cents":5,"skills":[{"id":"coder","name":"Coder","description":"Python code generator","tags":["code","python"]}]}'
  '{"name":"Summarizer Agent","description":"Summarizes long text into bullet points.","version":"1.0.0","docker_image":"a2a-agent-runtime:latest","price_per_invocation_cents":3,"skills":[{"id":"summarizer","name":"Summarizer","description":"Text summarizer","tags":["summarize","nlp"]}]}'
  '{"name":"Multi-Skill Agent","description":"One agent with multiple skills: research, code, summarize.","version":"1.0.0","docker_image":"a2a-agent-runtime:latest","price_per_invocation_cents":10,"skills":[{"id":"researcher","name":"Researcher","description":"QA","tags":["research"]},{"id":"coder","name":"Coder","description":"Code","tags":["code"]},{"id":"summarizer","name":"Summarizer","description":"Summarize","tags":["summarize"]}]}'
  '{"name":"Free Demo Agent","description":"A free agent for trying out the platform.","version":"0.1.0","docker_image":"a2a-agent-runtime:latest","price_per_invocation_cents":0,"skills":[{"id":"researcher","name":"Researcher","description":"Demo skill","tags":["demo"]}]}'
)

for agent_json in "${AGENTS[@]}"; do
  NAME=$(echo "$agent_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])")
  echo "  → deploying: $NAME"
  curl -s -X POST "$API/agents" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$agent_json" > /dev/null
done

echo
echo "==> Done. Visit http://localhost:3000 to browse the seeded agents."
echo "==> Sample credentials: demo@a2a.local / demo-pass-123"
