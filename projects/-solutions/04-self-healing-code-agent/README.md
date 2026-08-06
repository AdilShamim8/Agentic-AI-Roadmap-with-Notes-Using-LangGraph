# Self-healing code agent

A LangGraph-based autonomous agent that takes a **failing test** in a Python repo,
reproduces it, diagnoses the root cause, writes a patch, verifies it (no regressions),
and iterates with **reflexion** until the test passes or a max-iteration limit is hit.
On success it can open a GitHub pull request.

> Reference spec: [Project 04 — Self-healing code agent](https://github.com/AdilShamim8/Agentic-AI-Roadmap-with-Notes-and-Projects/tree/main/projects/04-self-healing-code-agent)

```
Failing test ──▶ Reproduce ──▶ Diagnose ──▶ Patch ──▶ Verify ──┬─▶ Pass ──▶ Open PR
                                                               │
                                                               └─▶ Fail ──▶ Reflexion ──▶ (retry) ──▶ Diagnose
                                                                                              │
                                                                                              └─▶ max iters ──▶ Report failure
```

## Highlights

- **LangGraph** state machine with plan-and-execute + reflexion loop.
- **Switchable LLM backend** — OpenAI GPT-4o *or* Anthropic Claude, via `LLM_PROVIDER`.
- **Multi-file patches** — agent can emit unified diffs touching >1 file; applied atomically.
- **Real integrations, env-gated** — LangSmith tracing and GitHub PR creation are wired but
  degrade gracefully when keys are absent.
- **Eval harness** — runs the agent over a fixture set and prints the 4 rubric metrics
  (pass rate, no-regression rate, cost per patch, trajectory efficiency).
- **3 demo fixtures** — ship-out-of-the-box end-to-end runs (no API key needed for the
  non-LLM parts).

## Quickstart

```bash
# 1. Install (uv recommended)
uv sync --all-extras

# 2. Configure
cp .env.example .env
#   set LLM_PROVIDER, OPENAI_API_KEY or ANTHROPIC_API_KEY

# 3. Run on a fixture (uses a mocked LLM if no key is present)
uv run self-heal run fixtures/case_01_off_by_one --test tests/test_calc.py::test_add

# 4. Run the eval harness over all fixtures
uv run self-heal-eval run --fixtures fixtures --max-iterations 3
```

## CLI

```
self-heal run REPO_PATH --test TEST_TARGET [--max-iterations N] [--no-pr] [--dry-run]
self-heal doctor                      # check env / API keys / tool availability
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — graph topology, state, nodes.
- [docs/EVALUATION.md](docs/EVALUATION.md) — eval harness, rubric, fixtures.
- [docs/EXTENDING.md](docs/EXTENDING.md) — adding LLM providers, tools, nodes.

## Status

Educational / portfolio reference implementation. Not affiliated with SWE-agent or SWE-bench.
