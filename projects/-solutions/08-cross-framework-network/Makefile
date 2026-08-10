# =============================================================================
# Cross-Framework Network — Makefile
# =============================================================================
# Common development commands. Run `make help` to see all targets.
# =============================================================================

.PHONY: help install dev-deps test test-cov lint format typecheck \
        start-research start-writer start-agents stop-agents \
        supervisor eval eval-quick demo clean docker-build docker-up docker-down docker-eval

PYTHON ?= python
PORT_RESEARCH ?= 8001
PORT_WRITER ?= 8002

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
install: ## Install project in development mode
	$(PYTHON) -m pip install -e ".[dev]"

dev-deps: ## Install development dependencies only
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install pytest pytest-asyncio pytest-cov

env: ## Create .env from .env.example
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env"; else echo ".env already exists"; fi

# -----------------------------------------------------------------------------
# Testing & Quality
# -----------------------------------------------------------------------------
test: ## Run the test suite
	$(PYTHON) -m pytest tests/ -v

test-cov: ## Run tests with coverage report
	$(PYTHON) -m pytest tests/ --cov=a2a --cov=agents --cov=supervisor --cov=llm --cov=eval --cov-report=term-missing

lint: ## Run ruff linter
	$(PYTHON) -m ruff check a2a agents supervisor llm eval tests

format: ## Format code with ruff
	$(PYTHON) -m ruff format a2a agents supervisor llm eval tests

typecheck: ## Run mypy type checking
	$(PYTHON) -m mypy a2a agents supervisor llm eval

# -----------------------------------------------------------------------------
# Local Services
# -----------------------------------------------------------------------------
start-research: ## Start the research agent A2A server (port 8001)
	$(PYTHON) -m agents.openai_research.server --port $(PORT_RESEARCH)

start-writer: ## Start the writer crew A2A server (port 8002)
	$(PYTHON) -m agents.crewai_writer.server --port $(PORT_WRITER)

start-agents: ## Start both A2A agent servers in the background
	@echo "Starting research agent on port $(PORT_RESEARCH)..."
	@nohup $(PYTHON) -m agents.openai_research.server --port $(PORT_RESEARCH) > /tmp/research-agent.log 2>&1 &
	@echo "Starting writer crew on port $(PORT_WRITER)..."
	@nohup $(PYTHON) -m agents.crewai_writer.server --port $(PORT_WRITER) > /tmp/writer-crew.log 2>&1 &
	@echo "Waiting for agents to start..."
	@sleep 3
	@echo "Agents started. Logs: /tmp/research-agent.log, /tmp/writer-crew.log"

stop-agents: ## Stop background A2A agent servers
	@-pkill -f "agents.openai_research.server" 2>/dev/null || true
	@-pkill -f "agents.crewai_writer.server" 2>/dev/null || true
	@echo "Agents stopped."

# -----------------------------------------------------------------------------
# Supervisor & Eval
# -----------------------------------------------------------------------------
supervisor: ## Run the supervisor (usage: make supervisor TASK="your task")
	@if [ -z "$(TASK)" ]; then \
		echo "Usage: make supervisor TASK=\"your task here\""; \
	else \
		$(PYTHON) -m supervisor.cli "$(TASK)"; \
	fi

eval: ## Run the full evaluation (20 tasks)
	$(PYTHON) -m eval.runner

eval-quick: ## Run a quick evaluation (first 3 tasks)
	$(PYTHON) -m eval.runner --limit 3

demo: start-agents ## Run a quick demo (starts agents, runs one task)
	@echo "Running demo task..."
	$(PYTHON) -m examples.demo
	$(MAKE) stop-agents

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------
docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start agent servers via Docker
	docker compose up -d research-agent writer-crew

docker-down: ## Stop all Docker services
	docker compose down

docker-supervisor: ## Run supervisor via Docker (usage: make docker-supervisor TASK="...")
	@if [ -z "$(TASK)" ]; then \
		echo "Usage: make docker-supervisor TASK=\"your task here\""; \
	else \
		docker compose run --rm supervisor "$(TASK)"; \
	fi

docker-eval: ## Run evaluation via Docker
	docker compose run --rm supervisor -c "python -m eval.runner --limit 5"

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------
clean: ## Remove build artifacts and cache
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ *.egg-info .coverage htmlcov 2>/dev/null || true
	@echo "Cleaned."
