SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

export PATH := $(HOME)/.local/bin:$(PATH)

AI_API_KEY ?=
ARGS ?=

.PHONY: setup run test clean help inspect

.DEFAULT_GOAL := help

setup:
	@echo "=== CaffiPilot Setup ==="
	@echo ""
	@echo "Checking project files..."
	@ls -la
	@echo ""
	@echo "Checking project structure..."
	@find . -maxdepth 2 -type f | sort | head -100
	@echo ""
	@echo "Checking project configuration files..."
	@find . -maxdepth 2 -type f \( \
		-name "pyproject.toml" \
		-o -name "package.json" \
		-o -name "uv.lock" \
		-o -name "poetry.lock" \
		-o -name "README*" \
		\) -print
	@echo ""
	@echo "Setup inspection complete."

run:
	@echo "Running CaffiPilot..."
	@echo "No run command configured yet."
	@echo "Run 'make inspect' to inspect the project structure."

test:
	@echo "Running tests..."
	@if command -v pytest >/dev/null 2>&1; then \
		AI_API_KEY="$(AI_API_KEY)" pytest; \
	else \
		echo "pytest is not installed."; \
		echo "Install/configure the project's test dependencies first."; \
	fi

clean:
	@echo "Cleaning CaffiPilot..."
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

inspect:
	@echo "=== Current Directory ==="
	@pwd
	@echo ""
	@echo "=== Files ==="
	@ls -la
	@echo ""
	@echo "=== Project Files ==="
	@find . -maxdepth 2 -type f | sort | head -100
	@echo ""
	@echo "=== Configuration Files ==="
	@find . -maxdepth 2 -type f \( \
		-name "pyproject.toml" \
		-o -name "package.json" \
		-o -name "uv.lock" \
		-o -name "poetry.lock" \
		-o -name "README*" \
		\) -print

help:
	@echo "CaffiPilot commands:"
	@echo ""
	@echo "  make setup      Inspect project and setup requirements"
	@echo "  make inspect    Inspect project structure"
	@echo "  make run        Run CaffiPilot"
	@echo "  make test       Run tests"
	@echo "  make clean      Clean generated Python files"
	@echo "  make help       Show this help"