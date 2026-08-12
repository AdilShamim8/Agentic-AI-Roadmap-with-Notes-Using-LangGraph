.PHONY: install dev-install test test-cov lint typecheck demo clean report help

PYTHON ?= python
PKG   := eval-harness

help:
	@echo "Available targets:"
	@echo "  install      Install runtime deps (pip install -r requirements.txt)"
	@echo "  dev-install  Install runtime + dev deps (editable)"
	@echo "  test         Run pytest"
	@echo "  test-cov     Run pytest with coverage"
	@echo "  lint         Run ruff"
	@echo "  typecheck    Run mypy"
	@echo "  demo         Run end-to-end demo (sample agent vs react dataset)"
	@echo "  report       Generate a fresh Markdown report"
	@echo "  clean        Remove build/test artifacts"

install:
	$(PYTHON) -m pip install -r requirements.txt

dev-install:
	$(PYTHON) -m pip install -e ".[dev,llm]"

test:
	$(PYTHON) -m pytest

test-cov:
	$(PYTHON) -m pytest --cov=eval --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check eval tests examples

typecheck:
	$(PYTHON) -m mypy eval

demo:
	$(PYTHON) -m eval run --agent eval.agents.sample_agents:ReActSampleAgent --dataset react --report-path reports/demo_react.md

report: demo
	@echo "Report written to reports/demo_react.md"

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
