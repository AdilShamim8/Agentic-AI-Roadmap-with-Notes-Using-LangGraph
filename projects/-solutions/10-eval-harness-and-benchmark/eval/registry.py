"""Benchmark registry loader.

The registry is a single YAML file (`benchmarks/registry.yaml`) that maps
each agent pattern to:

- the datasets appropriate for it,
- the evaluators that should run on each dataset,
- an optional baseline file for delta reporting.

Example YAML:

    patterns:
      - pattern: react
        description: "ReAct — reason + act loop"
        datasets: [react]
        evaluators:
          - name: exact_match
            kind: rule_based
          - name: llm_judge
            kind: llm_judge
            params:
              pass_threshold: 0.7
          - name: trajectory_match
            kind: trajectory
        baseline: baselines/baseline_v1.json
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from eval.schemas import PatternEntry


class Registry:
    """In-memory representation of `benchmarks/registry.yaml`."""

    def __init__(self, patterns: list[PatternEntry]) -> None:
        self._patterns: dict[str, PatternEntry] = {p.pattern: p for p in patterns}

    # ----- accessors -----------------------------------------------------

    def get(self, pattern: str) -> PatternEntry:
        try:
            return self._patterns[pattern]
        except KeyError as exc:
            available = ", ".join(sorted(self._patterns))
            raise KeyError(
                f"Unknown pattern {pattern!r}. Available: {available}."
            ) from exc

    def all_patterns(self) -> list[str]:
        return sorted(self._patterns)

    def datasets_for(self, pattern: str) -> list[str]:
        return self.get(pattern).datasets

    def evaluators_for(self, pattern: str):
        return self.get(pattern).evaluators

    def find_dataset_pattern(self, dataset: str) -> str:
        """Return the pattern that owns this dataset, or raise."""

        for name, entry in self._patterns.items():
            if dataset in entry.datasets:
                return name
        raise KeyError(f"Dataset {dataset!r} is not registered under any pattern.")

    # ----- construction --------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Registry":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        patterns_data: list[dict[str, Any]] = raw.get("patterns", [])
        patterns = [PatternEntry(**p) for p in patterns_data]
        return cls(patterns)

    @classmethod
    def default(cls) -> "Registry":
        """Load the default registry from `benchmarks/registry.yaml`."""

        from eval.config import get_settings

        return cls.from_yaml(get_settings().registry_path)

    # ----- introspection -------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {"patterns": [p.model_dump() for p in self._patterns.values()]}
