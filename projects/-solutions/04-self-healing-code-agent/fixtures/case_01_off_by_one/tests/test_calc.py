from calc import sum_range


def test_sum_range_basic():
    assert sum_range(1, 5) == 15  # 1+2+3+4+5


def test_sum_range_single():
    assert sum_range(7, 7) == 7


def test_sum_range_two():
    assert sum_range(3, 4) == 7
