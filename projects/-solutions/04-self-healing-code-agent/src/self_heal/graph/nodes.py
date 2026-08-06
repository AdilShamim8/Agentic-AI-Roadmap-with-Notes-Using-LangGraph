"""LangGraph node implementations.

Each node is a pure function `(state) -> partial state dict`. They use the
tools layer (git/pytest/fs/diff) and the LLM provider to do their work.
"""

from __future__ import annotations

from pathlib import Path

from self_heal.config import get_settings
from self_heal.graph import prompts
from self_heal.graph.state import AgentState, IterationRecord
from self_heal.llm.base import LLMProvider, LLMResponse, Message, TokenUsage
from self_heal.logging import get_logger
from self_heal.patches.diff import DiffError, apply_diff
from self_heal.tools.fs import read_relevant_files
from self_heal.tools.git import checkout_new_branch, commit_all, init_repo
from self_heal.tools.pytest_runner import run_pytest

log = get_logger(__name__)


# ── helper: call LLM and account for cost ─────────────────────
def _call_llm(
    provider: LLMProvider,
    state: AgentState,
    messages: list[Message],
) -> LLMResponse:
    resp = provider.complete(messages)

    tokens = state.get("tokens") or TokenUsage()
    tokens.input_tokens += resp.usage.input_tokens
    tokens.output_tokens += resp.usage.output_tokens

    state["llm_calls"] = state.get("llm_calls", 0) + 1
    state["tokens"] = tokens

    # Cost accounting.
    from self_heal.config import cost_for_model

    cost = cost_for_model(resp.model, resp.usage.input_tokens, resp.usage.output_tokens)
    state["cost_usd"] = state.get("cost_usd", 0.0) + cost

    # Budget guard.
    budget = get_settings().max_cost_usd
    if budget > 0 and state["cost_usd"] > budget:
        raise RuntimeError(f"Cost budget exceeded: ${state['cost_usd']:.4f} > ${budget:.4f}")
    return resp


# ── 1. reproduce ─────────────────────────────────────────────
def reproduce(state: AgentState) -> AgentState:
    """Run the target test, capture the traceback."""
    repo = Path(state["repo_path"])
    target = state["test_target"]

    log.info("agent.reproduce.start", repo=str(repo), target=target)
    result = run_pytest(repo, target, tb="long")

    if result.target_passed:
        # Already passing — nothing to do.
        log.info("agent.reproduce.already_passing")
        return {
            **state,
            "repro_result": result,
            "status": "passed",
        }

    log.info(
        "agent.reproduce.failed",
        exit_code=result.exit_code,
        failures=len(result.failures),
    )
    return {**state, "repro_result": result, "status": "running"}


# ── 2. diagnose ──────────────────────────────────────────────
def diagnose(state: AgentState, provider: LLMProvider) -> AgentState:
    """Ask the LLM to diagnose the failure."""
    repro = state.get("repro_result")
    if repro is None:
        raise RuntimeError("diagnose called before reproduce")

    repo = Path(state["repo_path"])
    tb = repro.failures[0].traceback if repro.failures else repro.stdout

    # Gather relevant source files from the traceback.
    files = read_relevant_files(repo, tb)
    source_block = (
        "\n\n".join(f"# File: {path}\n```python\n{content}\n```" for path, content in files.items())
        or "(no source files could be located from the traceback)"
    )

    messages = [
        Message(role="system", content=prompts.DIAGNOSE_SYSTEM),
        Message(
            role="user",
            content=prompts.DIAGNOSE_USER.format(
                test_target=state["test_target"],
                pytest_stdout=repro.stdout[:8000],
                traceback=tb[:8000],
                source_files=source_block,
            ),
        ),
    ]
    resp = _call_llm(provider, state, messages)
    log.info("agent.diagnose.done", model=resp.model, in_tokens=resp.usage.input_tokens)
    return {**state, "diagnosis": resp.content}


# ── 3. patch ─────────────────────────────────────────────────
def patch(state: AgentState, provider: LLMProvider) -> AgentState:
    """Ask the LLM to write a unified-diff patch."""
    diagnosis = state.get("diagnosis", "")
    reflexion = state.get("reflexion_notes", "(none)")
    previous_patch = state.get("patch_text", "(none)")
    repro = state.get("repro_result")
    tb = repro.failures[0].traceback if repro and repro.failures else ""

    repo = Path(state["repo_path"])
    files = read_relevant_files(repo, tb)
    source_block = (
        "\n\n".join(f"# File: {path}\n```python\n{content}\n```" for path, content in files.items())
        or "(no source files located)"
    )

    messages = [
        Message(role="system", content=prompts.PATCH_SYSTEM),
        Message(
            role="user",
            content=prompts.PATCH_USER.format(
                diagnosis=diagnosis,
                source_files=source_block,
                reflexion=reflexion,
                previous_patch=previous_patch,
            ),
        ),
    ]
    resp = _call_llm(provider, state, messages)
    patch_text = resp.content
    log.info("agent.patch.generated", chars=len(patch_text))

    if state.get("dry_run"):
        log.info("agent.patch.dry_run", msg="skipping apply")
        return {**state, "patch_text": patch_text, "patch_files": []}

    # Apply the patch.
    try:
        touched = apply_diff(repo, patch_text)
    except DiffError as exc:
        log.error("agent.patch.apply_failed", error=str(exc))
        # Record the failure; reflexion will pick it up.
        return {
            **state,
            "patch_text": patch_text,
            "patch_files": [],
            "reflexion_notes": f"PATCH APPLICATION FAILED: {exc}",
        }

    files_str = [str(p.relative_to(repo)) for p in touched]
    log.info("agent.patch.applied", files=files_str)
    return {**state, "patch_text": patch_text, "patch_files": files_str}


# ── 4. verify ────────────────────────────────────────────────
def verify(state: AgentState) -> AgentState:
    """Run the full test suite. Decide pass / fail / regression."""
    repo = Path(state["repo_path"])
    target = state["test_target"]

    # First: does the target now pass?
    target_result = run_pytest(repo, target, tb="long")

    if not target_result.target_passed:
        log.info("agent.verify.target_still_failing")
        return {**state, "verify_result": target_result}

    # Target passes — run the FULL suite to detect regressions.
    full_result = run_pytest(repo, None, tb="short")
    log.info(
        "agent.verify.full_suite",
        passed=full_result.passed,
        failed=full_result.failed,
        errors=full_result.errors,
    )

    if full_result.failed or full_result.errors:
        # We have regressions; surface them.
        full_result.target_passed = True  # target itself did pass
        return {**state, "verify_result": full_result}

    # Success.
    return {**state, "verify_result": full_result, "status": "passed"}


# ── 5. reflexion ─────────────────────────────────────────────
def reflexion(state: AgentState, provider: LLMProvider) -> AgentState:
    """Critique the failed patch for the next iteration."""
    verify_result = state.get("verify_result")
    repro = state.get("repro_result")

    tb = ""
    if verify_result and verify_result.failures:
        tb = verify_result.failures[0].traceback
    elif repro and repro.failures:
        tb = repro.failures[0].traceback

    messages = [
        Message(role="system", content=prompts.REFLEXION_SYSTEM),
        Message(
            role="user",
            content=prompts.REFLEXION_USER.format(
                iteration=state.get("iteration", 1),
                diagnosis=state.get("diagnosis", ""),
                patch=state.get("patch_text", ""),
                target_passed=bool(verify_result and verify_result.target_passed),
                failed=verify_result.failed if verify_result else 0,
                errors=verify_result.errors if verify_result else 0,
                traceback=tb[:6000],
            ),
        ),
    ]
    resp = _call_llm(provider, state, messages)
    log.info("agent.reflexion.done")
    return {**state, "reflexion_notes": resp.content}


# ── 6. submit ────────────────────────────────────────────────
def submit(state: AgentState) -> AgentState:
    """Commit the patch and (optionally) open a GitHub PR."""
    # Record this iteration into history (on the happy path, reflexion never
    # ran, so this is the only place the iteration gets captured).
    state = record_iteration(state)

    repo = Path(state["repo_path"])
    settings = get_settings()

    branch = state.get("work_branch") or "self-heal/patch"
    init_repo(repo)
    checkout_new_branch(repo, branch)
    sha = commit_all(
        repo, f"self-heal: fix {state['test_target']}\n\n{state.get('diagnosis', '')[:500]}"
    )
    log.info("agent.submit.committed", branch=branch, sha=sha[:8])

    pr_url: str | None = None
    if state.get("open_pr") and settings.has_github():
        from self_heal.github.pr import create_pull_request

        try:
            pr_url = create_pull_request(
                repo_path=repo,
                repo_full_name=settings.github_repo,
                token=settings.github_token,
                branch=branch,
                title=f"self-heal: fix {state['test_target']}",
                body=state.get("diagnosis", "")[:2000],
            )
            log.info("agent.submit.pr_opened", url=pr_url)
        except Exception as exc:
            log.error("agent.submit.pr_failed", error=str(exc))
            pr_url = None
    else:
        log.info("agent.submit.pr_skipped", reason="no_github_config_or_disabled")

    return {**state, "pr_url": pr_url}


# ── record + advance ─────────────────────────────────────────
def record_iteration(state: AgentState) -> AgentState:
    """Push the current per-iteration artifacts into `history` and bump `iteration`."""
    history: list[IterationRecord] = list(state.get("history") or [])
    iteration = state.get("iteration", 0) + 1
    record = IterationRecord(
        iteration=iteration,
        diagnosis=state.get("diagnosis", ""),
        patch_text=state.get("patch_text", ""),
        patch_files=list(state.get("patch_files") or []),
        verify=state.get("verify_result"),
        reflexion=state.get("reflexion_notes", ""),
        cost_usd=state.get("cost_usd", 0.0) - sum(r.cost_usd for r in history),
    )
    history.append(record)
    return {**state, "iteration": iteration, "history": history}


# ── routing ──────────────────────────────────────────────────
def route_after_verify(state: AgentState) -> str:
    """Decide where to go after `verify`."""
    if state.get("status") == "passed":
        return "submit"
    return "reflexion"


def route_after_reflexion(state: AgentState) -> str:
    """After reflexion, retry diagnose unless we're out of iterations."""
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations") or get_settings().max_iterations
    if iteration >= max_iter:
        log.warning("agent.exhausted", iteration=iteration, max=max_iter)
        return "end_exhausted"
    return "diagnose"
