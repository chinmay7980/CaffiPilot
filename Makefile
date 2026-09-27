SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

export PATH := $(HOME)/.local/bin:$(PATH)

AI_API_KEY ?=
ARGS ?=

.PHONY: setup run test clean help

.DEFAULT_GOAL := help

setup:
	@echo "Setting up CaffiPilot..."
	@python3 -m pip install -r requirements.txt

run:
	@AI_API_KEY="$(AI_API_KEY)" python3 main.py $(ARGS)

test:
	@AI_API_KEY="$(AI_API_KEY)" python3 -m pytest

clean:
	@echo "Cleaning CaffiPilot..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete

help:
	@echo "CaffiPilot commands:"
	@echo ""
	@echo "  make setup     Install dependencies"
	@echo "  make run       Run CaffiPilot"
	@echo "  make test      Run tests"
	@echo "  make clean     Clean generated Python files"
	@echo "  make help      Show this help"