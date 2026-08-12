"""Generate the baseline JSON report.

The baseline is just a previous RunReport's JSON serialised by the
reporter. We generate it by running each sample agent against its own
dataset with the mock LLM judge, then saving the report.

Run:
    python scripts/generate_baseline.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make sure we can import the eval package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("EVAL_LLM_PROVIDER", "mock")
os.environ.setdefault("EVAL_SEED", "42")
os.environ.setdefault("EVAL_PROJECT_ROOT", str(ROOT))

from eval.config import get_settings  # noqa: E402
from eval.evaluators import EvaluatorRegistry  # noqa: E402
from eval.registry import Registry  # noqa: E402
from eval.reporter import render_json  # noqa: E402
from eval.runner import (  # noqa: E402
    Runner,
    RunnerConfig,
    build_agent,
    build_evaluators,
)


AGENTS = {
    "react": "eval.agents.sample_agents:ReActSampleAgent",
    "plan_execute": "eval.agents.sample_agents:PlanExecuteSampleAgent",
    "supervisor": "eval.agents.sample_agents:SupervisorSampleAgent",
    "swarm": "eval.agents.sample_agents:SwarmSampleAgent",
    "map_reduce": "eval.agents.sample_agents:MapReduceSampleAgent",
}


def main() -> None:
    settings = get_settings()
    registry = Registry.default()

    # Use the react agent + react dataset as a representative baseline.
    pattern = "react"
    entry = registry.get(pattern)
    agent = build_agent(AGENTS[pattern])
    evaluators = build_evaluators(entry.evaluators)
    ds_path = str(settings.datasets_dir / f"{entry.datasets[0]}.jsonl")

    cfg = RunnerConfig.from_settings(settings)
    cfg.show_progress = False

    runner = Runner(
        agent=agent,
        dataset_path=ds_path,
        evaluators=evaluators,
        config=cfg,
    )
    report = runner.run()

    out_path = settings.baselines_dir / "baseline_v1.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_json(report), encoding="utf-8")

    s = report.summary
    print(f"\nBaseline written to: {out_path}")
    print(f"  pass_rate: {s.pass_rate:.3f}")
    print(f"  evaluator_scores: {s.evaluator_scores}")


if __name__ == "__main__":
    main()
