SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

# Ensure uv (installed via pipx / standalone) is on PATH
export PATH := $(HOME)/.local/bin:$(PATH)

# Optional overrides – can be set via env or `make run AI_API_KEY=...`
AI_API_KEY ?=
ARGS       ?=

.PHONY: setup run test clean help

.DEFAULT_GOAL := help

# ──────────────────────────────────────────
# setup  – install uv (if missing) + sync
# ──────────────────────────────────────────
setup:
	@echo "==> Checking for uv package manager..."
	@command -v uv >/dev/null 2>&1 || { \
		echo "==> Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}
	@echo "==> uv found: $$(uv --version)"
	@echo "==> Syncing workspace dependencies..."
	uv sync --all-packages
	@echo ""
	@echo "==> Copying .env.example → .env (if .env does not exist)..."
	@[ -f .env ] || cp .env.example .env
	@echo "✔  Setup complete! Run 'make run' to start CaffiPilot."

# ──────────────────────────────────────────
# run    – launch the AI Harness CLI / TUI
# ──────────────────────────────────────────
run:
	@echo "==> Launching AI-Harness..."
	AI_API_KEY="$(AI_API_KEY)" uv run python harness_cli.py $(ARGS)

# ──────────────────────────────────────────
# test   – run the test-suite
# ──────────────────────────────────────────
test:
	AI_API_KEY="$(AI_API_KEY)" uv run pytest $(ARGS)

# ──────────────────────────────────────────
# clean  – remove caches and virtualenvs
# ──────────────────────────────────────────
clean:
	@echo "==> Cleaning build artefacts..."
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache dist build *.egg-info
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@echo "✔  Clean complete."

# ──────────────────────────────────────────
# help   – show available targets
# ──────────────────────────────────────────
help:
	@echo ""
	@echo "╔══════════════════════════════════════════════════╗"
	@echo "║        CaffiPilot – Makefile Commands            ║"
	@echo "╠══════════════════════════════════════════════════╣"
	@echo "║  make setup       Install deps & create .env     ║"
	@echo "║  make run         Launch AI Harness CLI / TUI    ║"
	@echo "║  make test        Run the test suite              ║"
	@echo "║  make clean       Remove caches & virtualenvs     ║"
	@echo "║  make help        Show this help message          ║"
	@echo "╚══════════════════════════════════════════════════╝"
	@echo ""
	@echo "  Optional variables:"
	@echo "    AI_API_KEY=...   LLM API key (or set in .env)"
	@echo "    ARGS='...'       Extra arguments for run/test"
	@echo ""