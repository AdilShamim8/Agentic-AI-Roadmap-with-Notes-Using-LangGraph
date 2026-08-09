# =============================================================================
# Makefile - common developer commands
# =============================================================================
.PHONY: help install dev lint format typecheck test test-unit test-integration run-local run-kafka docker-up docker-down seed eval clean

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

help:
	@echo "Anomaly Monitor - common targets"
	@echo "  install         install runtime deps (editable)"
	@echo "  dev             install runtime + dev deps"
	@echo "  lint            run ruff"
	@echo "  format          run ruff --fix + format"
	@echo "  typecheck       run mypy"
	@echo "  test            run unit tests"
	@echo "  test-integration run integration tests (needs Kafka/Redis/OpenAI)"
	@echo "  run-local       run pipeline in synthetic local mode"
	@echo "  run-kafka       run pipeline against docker-compose stack"
	@echo "  docker-up       start Kafka + Redis + Prometheus via docker compose"
	@echo "  docker-down     stop docker-compose stack"
	@echo "  seed            generate 1h of synthetic log data into data/generated/"
	@echo "  eval            run eval suite against synthetic labeled data"
	@echo "  clean           remove build/test/runtime artifacts"

install:
	$(PIP) install -e .

dev:
	$(PIP) install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check src tests eval

format:
	$(PYTHON) -m ruff check --fix src tests eval
	$(PYTHON) -m ruff format src tests eval

typecheck:
	$(PYTHON) -m mypy src

test:
	$(PYTHON) -m pytest -m "not integration" -v

test-unit: test

test-integration:
	$(PYTHON) -m pytest -m "integration" -v

run-local:
	ANOMON_MODE=local $(PYTHON) -m anomaly_monitor.cli run

run-kafka:
	ANOMON_MODE=kafka $(PYTHON) -m anomaly_monitor.cli run

docker-up:
	docker compose up -d

docker-down:
	docker compose down

seed:
	$(PYTHON) -m data.generator --hours 1 --out data/generated/synthetic_1h.jsonl

eval:
	$(PYTHON) -m eval.run_eval --data data/samples/anomalous.jsonl --labels data/samples/labels.jsonl

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov .runtime build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
