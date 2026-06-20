# DryRun — make targets.
# The guaranteed-running mock base needs only: `make install` then `make demo`.

DRYRUN_MODE ?= mock
export DRYRUN_MODE

.DEFAULT_GOAL := help

.PHONY: help install install-agents test demo mock live api web web-install agents stop clean

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
	@uv run dryrun --demo

mock: ## Run the cascade in mock mode
	@DRYRUN_MODE=mock uv run dryrun --demo

live: ## Run the cascade in live mode (falls back to mock on any failure)
	@DRYRUN_MODE=live uv run dryrun --demo

api: ## Start the FastAPI gateway the frontend talks to (:8000)
	@port=$${DRYRUN_API_PORT:-8000}; \
	if lsof -ti :$$port >/dev/null 2>&1; then \
		echo "Port $$port is already in use. Run \`make stop\` or set DRYRUN_API_PORT."; \
		exit 1; \
	fi; \
	uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port $$port

web-install: ## Install the frontend dependencies
	cd apps/web && npm install

web: ## Start the Next.js frontend in dev mode (mock mode)
	cd apps/web && npm install && npm run dev

web-prod: ## Build + serve the frontend production build (snappy; use for demos)
	cd apps/web && npm install && npm run build && npm run start

agents: ## Launch all uAgents together in one Bureau (:8200; needs `make install-agents`)
	DRYRUN_BUREAU_PORT=$${DRYRUN_BUREAU_PORT:-8200} uv run --extra agents python -m dryrun_agents.launch

stop: ## Stop dev servers on :8000 (API), :8200 (Bureau), :3000 (web)
	-@for port in 8000 8200 3000; do \
		pids=$$(lsof -ti :$$port 2>/dev/null); \
		if [ -n "$$pids" ]; then kill $$pids 2>/dev/null || true; fi; \
	done

clean: ## Remove build/test caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__ **/*.egg-info
