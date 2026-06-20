# DryRun — make targets.
# The guaranteed-running mock base needs only: `make install` then `make demo`.

DRYRUN_MODE ?= mock
export DRYRUN_MODE

.DEFAULT_GOAL := help

.PHONY: help install install-agents test demo mock live api web web-install agents clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install Python deps for the mock demo (light, no agent framework)
	uv sync

install-agents: ## Install everything incl. the uagents framework (Phase 4/5)
	uv sync --extra agents

test: ## Run the core + provider test suite (no network)
	uv run pytest

demo: ## Run the full cascade end to end on bundled demo inputs, print JSON report
	uv run dryrun --demo

mock: ## Run the cascade in mock mode
	DRYRUN_MODE=mock uv run dryrun --demo

live: ## Run the cascade in live mode (falls back to mock on any failure)
	DRYRUN_MODE=live uv run dryrun --demo

api: ## Start the FastAPI gateway the frontend talks to
	uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port $${DRYRUN_API_PORT:-8000}

web-install: ## Install the frontend dependencies
	cd apps/web && npm install

web: ## Start the Next.js frontend (mock mode)
	cd apps/web && npm install && npm run dev

agents: ## Launch all uAgents locally (Phase 4/5)
	uv run python -m dryrun_agents.launch

clean: ## Remove build/test caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__ **/*.egg-info
