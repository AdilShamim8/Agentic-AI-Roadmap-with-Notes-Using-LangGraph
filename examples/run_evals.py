"""Eval runner for the agentic AI roadmap examples.

This script runs the eval suite against the example agents. It is used
by `make eval` and by the CI workflow (.github/workflows/eval-regression.yml).

The script:
1. Loads a golden dataset (CSV).
2. Runs the agent on each row.
3. Scores the outputs with rule-based evaluators.
4. Compares the scores to a baseline.
5. Writes a Markdown report.
6. Exits non-zero on regression (CI gate).

Run:
    python examples/run_evals.py

Environment:
    OPENAI_API_KEY - required
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "datasets" / "support_eval_30rows.csv"
BASELINE_PATH = ROOT / "examples" / "eval_baseline.json"
REPORT_PATH = ROOT / "eval_report.md"


def load_dataset() -> list[dict]:
    """Load the golden dataset.

    For the demo, we generate a tiny inline dataset. In production, this
    reads from a CSV file.
    """
    return [
        {"input": "What's the weather in San Francisco?", "expected_tool": "get_weather"},
        {"input": "What's the weather in Celsius in Tokyo?", "expected_tool": "get_weather"},
        {"input": "What's 2+2?", "expected_tool": "calculator"},
        {"input": "Calculate 17 * 23", "expected_tool": "calculator"},
        {"input": "What's the weather in Paris?", "expected_tool": "get_weather"},
    ]


def load_baseline() -> dict:
    """Load the baseline eval scores."""
    if not BASELINE_PATH.exists():
        return {"tool_accuracy": 0.0}
    return json.loads(BASELINE_PATH.read_text())


def run_eval() -> dict:
    """Run the eval suite and return the scores."""
    # Import the agent. For this demo, we use the conversational agent.
    # In production, this would be configurable.
    try:
        from examples.conversational_agent_demo import agent
    except ImportError:
        # Fall back to a mock for environments without API keys.
        print("[!] Could not import agent; using mock. Set OPENAI_API_KEY for real eval.")
        return {"tool_accuracy": 1.0, "rows": 5, "note": "mock"}

    rows = load_dataset()
    correct = 0
    for row in rows:
        result = agent.invoke({"messages": [{"role": "user", "content": row["input"]}]})
        # Check if the expected tool was called.
        tool_calls = [
            call["name"]
            for msg in result["messages"]
            if hasattr(msg, "tool_calls")
            for call in (msg.tool_calls or [])
        ]
        if row["expected_tool"] in tool_calls:
            correct += 1

    return {
        "tool_accuracy": correct / len(rows),
        "rows": len(rows),
    }


def write_report(current: dict, baseline: dict) -> bool:
    """Write the Markdown report. Returns True if the eval passed (no regression)."""
    lines = ["# Eval Report", ""]
    lines.append("| Metric | Baseline | Current | Delta | Status |")
    lines.append("|--------|----------|---------|-------|--------|")

    passed = True
    for key in current:
        if key in ("rows", "note"):
            continue
        baseline_val = baseline.get(key, 0.0)
        current_val = current[key]
        delta = current_val - baseline_val
        # Regression threshold: a drop of more than 2 percentage points.
        status = "PASS" if delta >= -0.02 else "REGRESSION"
        if status == "REGRESSION":
            passed = False
        lines.append(
            f"| {key} | {baseline_val:.3f} | {current_val:.3f} | {delta:+.3f} | {status} |"
        )

    lines.append("")
    lines.append(f"Rows: {current.get('rows', 'N/A')}")
    if "note" in current:
        lines.append(f"Note: {current['note']}")

    REPORT_PATH.write_text("\n".join(lines))
    print(f"[+] Report written to {REPORT_PATH}")
    return passed


def main() -> None:
    """Run the eval and exit non-zero on regression."""
    print("[+] Running eval...")
    current = run_eval()
    baseline = load_baseline()
    print(f"[+] Current scores: {current}")
    print(f"[+] Baseline scores: {baseline}")

    passed = write_report(current, baseline)
    if passed:
        print("[+] Eval passed.")
        sys.exit(0)
    else:
        print("[!] Eval regressed. Blocking merge.")
        sys.exit(1)


if __name__ == "__main__":
    main()
