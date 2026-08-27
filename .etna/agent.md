# Agent Etna — Contract & Guardrails

This file is maintained automatically by **Agent Etna** for **01 research agent**.
It is this agent's behavioral **contract**: what it's for, who it serves, what's
in and out of scope, plus a log of every change Etna has applied — so the whole
footprint is visible and auditable in your own repo.

_Maintained by Agent Etna. Don't edit by hand — it is rewritten on every shipped change._

## Agent
- **Repo:** `AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects` (branch `main`)

## Behavioral contract
- **Purpose:** An autonomous research agent that takes a topic, breaks it down into sub-questions, searches the web and local documents, synthesizes findings into a cited Markdown report, critiques its own draft for gaps, and refines it in a second research pass if needed.
- **Calibration level:** Foundational — basics first

## Guardrails
- Stay focused on this purpose: An autonomous research agent that takes a topic, breaks it down into sub-questions, searches the web and local documents, synthesizes findings into a cited Markdown report, critiques its own draft for gaps, and refines it in a second research pass if needed.

## Change history

### 2026-08-27 · Cycle 1 · 1 change · merged
- **safety:memory-retention** — Narrowly encodes that user-supplied conversational tracking tokens like REF-077BF4 should be echoed on request, while explicitly preserving refusal for secrets/credentials that tripped the prior draft's safety regression.
