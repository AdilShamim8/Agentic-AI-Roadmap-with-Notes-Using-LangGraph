"""Tests for the registry loader."""

from __future__ import annotations

import pytest

from eval.registry import Registry


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry.default()


def test_loads_all_patterns(registry: Registry):
    patterns = registry.all_patterns()
    assert set(patterns) == {
        "react",
        "plan_execute",
        "supervisor",
        "swarm",
        "map_reduce",
    }


def test_get_pattern(registry: Registry):
    entry = registry.get("react")
    assert entry.pattern == "react"
    assert "react" in entry.datasets
    assert any(e.name == "exact_match" for e in entry.evaluators)


def test_unknown_pattern_raises(registry: Registry):
    with pytest.raises(KeyError):
        registry.get("does-not-exist")


def test_find_dataset_pattern(registry: Registry):
    assert registry.find_dataset_pattern("react") == "react"
    assert registry.find_dataset_pattern("plan_execute") == "plan_execute"
    with pytest.raises(KeyError):
        registry.find_dataset_pattern("not-a-dataset")


def test_baseline_path_set(registry: Registry):
    for name in registry.all_patterns():
        entry = registry.get(name)
        assert entry.baseline is not None
        assert entry.baseline.endswith("baseline_v1.json")
