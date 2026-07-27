.PHONY: install dev lint test eval build clean help

PYTHON ?= python3
PIP ?= pip

help:
	@echo "Available targets:"
	@echo "  make install   - install runtime dependencies"
	@echo "  make dev       - install dev dependencies (pytest, ruff, mypy, jupyter)"
	@echo "  make lint      - run ruff + mypy"
	@echo "  make test      - run pytest"
	@echo "  make eval      - run the eval suite against all example agents"
	@echo "  make build     - build the docker image"
	@echo "  make clean     - remove caches and build artifacts"

install:
	$(PIP) install -e .

dev:
	$(PIP) install -e ".[dev]"

lint:
	ruff check examples/ tests/
	mypy examples/

test:
	pytest -v

eval:
	$(PYTHON) examples/run_evals.py

build:
	docker build -t agentic-ai-roadmap:latest .

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
