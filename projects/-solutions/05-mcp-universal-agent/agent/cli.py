"""Command-line entry point for the universal MCP agent.

Usage::

    # one-shot goal
    python3 -m agent.cli "List every file in the sandbox"

    # interactive REPL
    python3 -m agent.cli --interactive

    # override the selection strategy for one run
    MCP_AGENT_SELECTION_STRATEGY=categorized python3 -m agent.cli "What is 25 * 17?"

    # limit discovery to a subset of servers (faster startup)
    python3 -m agent.cli --only filesystem,calculator "Read sample.txt and count its words"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Make sure the project root is on sys.path so ``mcp_servers.*`` resolves
# when the agent spawns server subprocesses.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent.graph import run_agent  # noqa: E402  (after sys.path tweak)


def _load_dotenv() -> None:
    """Tiny .env loader – avoids adding python-dotenv as a dependency."""
    env_path = _ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


async def _run_once(goal: str, args: argparse.Namespace) -> int:
    only = args.only.split(",") if args.only else None
    result = await run_agent(
        user_goal=goal,
        registry_path=args.registry,
        only=only,
        selection_strategy=args.strategy,
        verbose=args.verbose,
    )
    print("\n" + "=" * 72)
    print("ANSWER")
    print("=" * 72)
    print(result["answer"])
    if args.verbose:
        print("\n" + "-" * 72)
        print(f"provider={result['provider']}  strategy={result['strategy']}  "
              f"iterations={result['iterations']}  "
              f"tools_offered_total={result['tools_offered_total']}")
        print("-" * 72)
        for i, step in enumerate(result["trace"]):
            print(f"  [{i:02d}] {step.get('step'):8s}  "
                  f"{step.get('rationale') or step.get('tool') or (step.get('text') or '')[:80]}")
    if args.json:
        print("\n" + "-" * 72)
        print("TRACE (JSON)")
        print("-" * 72)
        print(json.dumps(result, indent=2, default=str))
    return 0


async def _interactive(args: argparse.Namespace) -> int:
    print("Universal MCP Agent – interactive mode. Type 'exit' or Ctrl-D to quit.")
    print(f"  strategy = {os.environ.get('MCP_AGENT_SELECTION_STRATEGY', 'retrieval')}")
    print(f"  registry = {args.registry}")
    print()
    while True:
        try:
            goal = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return 0
        if not goal:
            continue
        if goal.lower() in {"exit", "quit", ":q"}:
            return 0
        try:
            await _run_once(goal, args)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        print()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="agent.cli",
        description="Universal MCP agent – discovers MCP servers from a registry "
                    "and accomplishes a user goal by composing their tools.",
    )
    p.add_argument("goal", nargs="?", help="The user goal to accomplish.")
    p.add_argument("--interactive", "-i", action="store_true",
                   help="Start an interactive REPL instead of running one goal.")
    p.add_argument("--registry", default=str(_ROOT / "registry.json"),
                   help="Path to registry.json (default: ./registry.json).")
    p.add_argument("--only", default=None,
                   help="Comma-separated list of server names to limit discovery to.")
    p.add_argument("--strategy", default=None,
                   choices=["naive", "categorized", "retrieval"],
                   help="Override the tool-selection strategy for this run.")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Print the agent trace to stderr.")
    p.add_argument("--json", action="store_true",
                   help="Print the full trace as JSON after the answer.")
    return p.parse_args()


def main() -> int:
    _load_dotenv()
    args = _parse_args()
    if args.interactive:
        return asyncio.run(_interactive(args))
    if not args.goal:
        print("error: provide a goal or use --interactive", file=sys.stderr)
        return 2
    return asyncio.run(_run_once(args.goal, args))


if __name__ == "__main__":
    raise SystemExit(main())
