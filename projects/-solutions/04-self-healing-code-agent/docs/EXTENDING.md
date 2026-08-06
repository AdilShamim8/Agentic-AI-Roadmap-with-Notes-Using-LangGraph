# Extending

## Adding an LLM provider

1. Implement the `LLMProvider` protocol from `src/self_heal/llm/base.py`:

   ```python
   from self_heal.llm.base import LLMResponse, Message, TokenUsage

   class MyProvider:
       name = "myllm"
       model = "my-model-v1"

       def complete(self, messages: list[Message]) -> LLMResponse:
           # call your backend, return LLMResponse with usage + content
           ...
   ```

2. Register it in `provider_factory()` (`src/self_heal/llm/base.py`) by
   adding a branch:

   ```python
   if s.llm_provider.value == "myllm":
       from self_heal.llm.my_provider import MyProvider
       return MyProvider(s)
   ```

3. Add the provider name to the `LLMProviderName` enum in
   `src/self_heal/config.py`.

4. Add a cost entry to `COST_TABLE_USD_PER_M` so cost accounting works.

## Adding a tool

Tools are plain Python functions in `src/self_heal/tools/`. To add a new one:

1. Write the function in a new module under `tools/` (or an existing one).
2. Re-export it from `tools/__init__.py`.
3. Call it from a node in `src/self_heal/graph/nodes.py`.

There is no tool-registration mechanism — the agent's "tools" are not
exposed to the LLM as callable functions; instead, the LLM emits structured
output (a diagnosis, a diff) and the nodes call tools on the LLM's behalf.
This is the same plan-and-execute shape the spec calls for, and it avoids
the security pitfalls of letting the LLM run arbitrary shell.

## Adding a graph node

1. Write the node function in `src/self_heal/graph/nodes.py`. Signature is
   `(state) -> partial state` (or `(state, provider) -> partial state` for
   LLM-using nodes).
2. Register it in `build_agent_graph()` in `src/self_heal/graph/builder.py`:

   ```python
   graph.add_node("my_node", my_node_fn)
   graph.add_edge("some_node", "my_node")
   graph.add_conditional_edges("my_node", router_fn, {"a": "a", "b": "b"})
   ```

3. If the node needs new state fields, add them to `AgentState` in
   `src/self_heal/graph/state.py`.

## Adding a fixture case

1. Create `fixtures/case_XX_name/` with the layout described in
   [EVALUATION.md](./EVALUATION.md).
2. Write a buggy source file and a failing test.
3. Add `case.json` with `target_test` and `bug_summary`.
4. (Optional) Add `expected_patch.diff` as a gold reference.
5. Run `uv run self-heal-eval run --only case_XX_name` to verify.

## Configuring for production

| env var | purpose |
|---------|---------|
| `LLM_PROVIDER` | `openai` \| `anthropic` \| `mock` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | provider auth |
| `OPENAI_MODEL` / `ANTHROPIC_MODEL` | model name |
| `SELF_HEAL_MAX_ITERATIONS` | default max loop iterations |
| `SELF_HEAL_MAX_COST_USD` | per-run spend cap; `0` disables |
| `LANGSMITH_API_KEY` + `LANGSMITH_TRACING=true` | enable trajectory tracing |
| `GITHUB_TOKEN` + `GITHUB_REPO` | enable PR creation in `submit` |

## Security notes

- The agent runs `git` and `pytest` as subprocesses in the target repo. Do
  not point it at untrusted repositories — `pytest` can execute arbitrary
  code via `conftest.py` or test modules.
- The diff applier writes files under the target repo only; it never writes
  outside `repo_path`. Paths in the diff that resolve outside the repo are
  rejected by `read_relevant_files` and would be rejected by `apply_diff`
  via the `Path` join (the target path is always `repo_path / new_path`).
- GitHub PR creation requires push access to the configured repo; scope the
  token accordingly.
