.PHONY: install dev test lint typecheck eval run smoke clean

install:
	uv sync --all-extras

dev:
	uv sync --all-extras --dev

test:
	uv run pytest -ra

lint:
	uv run ruff check src evals tests
	uv run ruff format --check src evals tests

typecheck:
	uv run mypy src/self_heal evals

smoke:
	uv run python -m self_heal doctor
	uv run self-heal run fixtures/case_01_off_by_one --test tests/test_calc.py::test_sum_range_basic --no-pr

eval:
	uv run self-heal-eval run --fixtures fixtures --max-iterations 3

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
