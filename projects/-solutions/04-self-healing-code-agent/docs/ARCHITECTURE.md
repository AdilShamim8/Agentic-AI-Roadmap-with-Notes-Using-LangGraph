# Architecture

## Overview

The self-healing agent is a **LangGraph state machine** that loops over a
failing test until it either fixes the test or exhausts a max-iteration
budget. Each iteration runs four LLM-driven nodes — `reproduce`, `diagnose`,
`patch`, `verify` — plus a `reflexion` step that critiques a failed patch
before retrying.

```
START
  │
  ▼
reproduce ──(already passing)──▶ submit ──▶ END
  │ (failing)
  ▼
diagnose ◀──────────────────────┐
  │                             │
  ▼                             │
patch                           │ (retry)
  │                             │
  ▼                             │
verify                          │
  │                             │
  ├──(passed)──▶ submit ──▶ END │
  │                             │
  ▼ (failed)                    │
reflexion ──────────────────────┘
  │
  ▼ (max iterations)
END (exhausted)
```

## State

The graph's state is a single `AgentState` TypedDict (see
`src/self_heal/graph/state.py`). Every node reads from and writes to this dict.
Key fields:

| field | meaning |
|-------|---------|
| `repo_path` | absolute path to the target Python repo |
| `test_target` | pytest nodeid, e.g. `tests/test_calc.py::test_add` |
| `iteration` | current iteration number (1-indexed after first record) |
| `max_iterations` | hard cap; on reaching it the loop ends `exhausted` |
| `reproduce` | the `PytestResult` from the initial failing run |
| `diagnosis` | the LLM's prose diagnosis of the failure |
| `patch_text` | the LLM's unified-diff patch text |
| `patch_files` | list of repo-relative paths the patch touched |
| `verify` | the `PytestResult` after applying the patch |
| `reflexion` | the LLM's critique of a failed patch |
| `history` | list of `IterationRecord` (one per completed loop) |
| `status` | `running` \| `passed` \| `failed` \| `exhausted` \| `error` |
| `llm_calls` | running count of LLM completions |
| `cost_usd` | running USD cost estimate |
| `pr_url` | GitHub PR URL if `submit` opened one |

## Nodes

All nodes live in `src/self_heal/graph/nodes.py` and are plain functions
`(state) -> partial state`. LLM-using nodes take the provider as a second
argument and are bound into single-arg functions via `functools.partial` at
graph-build time, so the LangGraph wiring stays clean.

### `reproduce`
Runs `pytest <test_target> --tb=long` in the repo, parses the result into a
`PytestResult`, and extracts per-test tracebacks. If the target already
passes, jumps straight to `submit` (nothing to fix).

### `diagnose`
Reads the traceback, locates the source files referenced in it via
`read_relevant_files()`, and prompts the LLM to produce a structured
diagnosis: root cause, suspect location, hypothesis, confidence. No code is
written in this step.

### `patch`
Hands the LLM the diagnosis, the relevant source files, and (on retry) the
previous failed patch + reflexion notes. Asks for a unified diff. The diff is
parsed and applied via `apply_diff()` (see Patches below). If application
fails, the failure reason is recorded as a reflexion note and the loop
continues.

### `verify`
Two-phase:
1. Run just the target test. If it still fails, go to `reflexion`.
2. If the target passes, run the **full** test suite to detect regressions.
   Any failure or error → `reflexion`. Otherwise → `submit`.

### `reflexion`
LLM critiques the failed patch: what went wrong, what to try next, pitfalls
to avoid. The critique is stored in `state.reflexion` and fed back into the
next `patch` call. Then `record_iteration` snapshots the current per-iteration
artifacts into `state.history` and bumps `iteration`.

### `submit`
Commits the patch on a `self-heal/patch` branch. If `open_pr=True` and
GitHub credentials are configured, pushes the branch and opens a PR via the
GitHub REST API. Otherwise just leaves the local commit.

## Patches (the multi-file stretch goal)

`src/self_heal/patches/diff.py` implements a from-scratch unified-diff parser
and applier. It supports:

- **Multi-file diffs** — a single diff blob can contain multiple
  `---`/`+++` blocks, each applied to its own file.
- **New files** — `--- /dev/null` → `+++ b/new.py`.
- **Deleted files** — `--- a/old.py` → `+++ /dev/null`.
- **Fuzzy context matching** — if the recorded `@@ -old_start` line number has
  drifted (e.g. because an earlier hunk in the same diff shifted lines), the
  applier searches a ±20-line window for the recorded context.
- **Atomic failure** — if any hunk fails to apply, `DiffError` is raised; the
  caller should `git checkout` to revert partial writes.

## LLM provider abstraction

`src/self_heal/llm/base.py` defines a `LLMProvider` Protocol with one method:
`complete(messages) -> LLMResponse`. Three implementations:

| provider | when used |
|----------|-----------|
| `OpenAIProvider` | `LLM_PROVIDER=openai` and `OPENAI_API_KEY` set |
| `AnthropicProvider` | `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` set |
| `MockProvider` | `LLM_PROVIDER=mock`, or when the requested provider's key is missing |

The mock implements a tiny pattern-matching heuristic so the agent can run
end-to-end on the bundled fixtures with **zero API keys**. It is not a
general code agent — it only knows how to reason about the specific bug
shapes in `fixtures/`. For real work, configure OpenAI or Anthropic.

## Cost accounting

`src/self_heal/config.py` ships a `COST_TABLE_USD_PER_M` mapping model →
{input, output} USD-per-million-tokens. Each `LLMResponse` carries a
`TokenUsage`; the `_call_llm` helper in `nodes.py` updates
`state.cost_usd` and `state.llm_calls` after every call. If
`SELF_HEAL_MAX_COST_USD > 0` and spend exceeds it, the agent raises
`RuntimeError` and the run aborts.

## Observability

LangSmith tracing is wired through `langchain_core`'s env-var hooks. The
`maybe_enable_tracing()` call in `SelfHealAgent.__init__` sets
`LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` + `LANGSMITH_PROJECT` if a
key is configured; otherwise it's a no-op. Trajectories (every LLM call,
every tool invocation) then show up in LangSmith under the configured
project — critical for the trajectory-efficiency rubric metric.

## Failure modes

| failure | behavior |
|---------|----------|
| LLM API error | `tenacity` retries 4× with exponential backoff |
| Patch application fails | recorded as reflexion note; loop continues |
| Cost budget exceeded | `RuntimeError`; run ends with `status=error` |
| Max iterations hit | run ends with `status=exhausted` |
| Test already passing | skips diagnose/patch/verify; goes straight to submit |
