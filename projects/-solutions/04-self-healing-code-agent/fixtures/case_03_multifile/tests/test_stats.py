import pytest

from mathlib.indexing import select
from mathlib.stats import percentile


def test_select_basic():
    assert select([10, 20, 30, 40], 0) == 10
    assert select([10, 20, 30, 40], 3) == 40


def test_percentile_50():
    # 50th percentile of [10,20,30,40,50] should be 30 (the median).
    assert percentile([10, 20, 30, 40, 50], 50) == 30


def test_percentile_100():
    assert percentile([10, 20, 30, 40, 50], 100) == 50


def test_percentile_empty():
    with pytest.raises(ValueError):
        percentile([], 50)


def test_percentile_invalid_pct():
    with pytest.raises(ValueError):
        percentile([1, 2, 3], 150)
