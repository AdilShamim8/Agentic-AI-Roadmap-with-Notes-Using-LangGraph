

## Improvements (approved via Agent Etna simulations)
- Narrowly encodes that user-supplied conversational tracking tokens like REF-077BF4 should be echoed on request, while explicitly preserving refusal for secrets/credentials that tripped the prior draft's safety regression.
  > {"topic":"User-provided reference/tracking codes","rule":"When the user explicitly asks the agent to remember and later repeat back a reference code they themselves supplied (pattern like 'REF-XXXXXX' introduced by the user as a tracking token for this conversation), reproduce the exact token verbatim on request. This applies ONLY to non-secret tracking identifiers the user asked to be echoed; it does NOT apply to API keys, passwords, credentials, PII, or anything the user did not explicitly ask to be repeated — existing refusal behaviour for those cases still applies unchanged.","example":"User: 'Remember REF-077BF4.' Later: 'What was the code?' → Reply with 'REF-077BF4'."}
  This change is not sufficient on its own.
  This agent has nowhere to remember anything between messages.
  The pull request wires this up in the agent's code. It will not work until you have actually created the store and given the agent its connection details — that part is yours, and nothing we ship can do it for you.
  We looked at projects/-solutions/01-research-agent/requirements.txt, the repository file list (7 files), the environment variables this agent declares and found nothing that persists between conversations. If this agent does have a store we missed, say so and we'll work from that instead.
  Options that fit this agent:
  - SQLite file — lowest — a file next to the agent, no account, no cost (better-sqlite3). Lost whenever the filesystem is replaced, which on most hosts is every deploy.
  - A hosted Postgres (Supabase, Neon, Render, RDS) — moderate — an account, a connection string, one table (pg). Survives deploys and scales past one instance. The usual right answer.
  - A hosted Redis (Upstash, Redis Cloud) — low — an account and a URL (ioredis). Ideal for recent conversation state; set an expiry, and don't use it as the only copy of anything you need next month.
