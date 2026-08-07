# Engineering Notes

## Architecture decisions

- **MCP-first**: every capability the agent can use is exposed through an MCP
  server. The agent has no built-in tools of its own. This keeps the agent
  core tiny and pushes all side-effects behind the protocol boundary.
- **Stdio transport**: servers are local subprocesses spawned on demand.
  For multi-host deployments switch to SSE / WebSocket transport in
  `registry.json` – no agent code changes required.
- **Tool selection**: default strategy is `retrieval` because the registry
  ships 5 servers × ~4 tools = 20 tools, which already starts to degrade
  naive GPT-4o-mini selection accuracy. Switch to `categorized` for a
  cheaper two-stage call, or `naive` for a baseline.

## Lessons learned (so far)

1. Tool description wording matters more than model size. Re-writing
   "calculate X" as "evaluate the arithmetic expression X and return the
   numeric result" measurably improved selection accuracy.
2. Embedding-based retrieval works with a trivial TF-IDF embedding. You do
   NOT need OpenAI ada-002 to get >85% selection accuracy on 20 tools.
3. Always include a "no tool needed" exit path in the prompt, otherwise the
   agent will invent spurious tool calls when the answer is already in the
   conversation.
