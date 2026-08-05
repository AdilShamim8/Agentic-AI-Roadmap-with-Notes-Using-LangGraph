.PHONY: help install ingest ask ui mcp eval test reset clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (use venv recommended)
	pip install -r requirements.txt
	pip install -e .

ingest: ## Ingest everything in data/ingest/
	python scripts/ingest.py data/ingest

ingest-eval: ## Ingest the eval sample dataset
	python scripts/ingest.py eval/data/documents

ask: ## Ask a question (usage: make ask Q="...")
	python scripts/ask.py "$(Q)"

ui: ## Launch Streamlit UI
	streamlit run app.py

mcp: ## Launch the MCP tool server
	python -m knowledge_manager.mcp.server

eval: ## Run eval harness
	python eval/run_eval.py

test: ## Run unit tests
	pytest -q

reset: ## Wipe the local DB and graph
	python scripts/reset_db.py

clean: ## Remove caches and build artifacts
	rm -rf __pycache__ .pytest_cache .ruff_cache build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
