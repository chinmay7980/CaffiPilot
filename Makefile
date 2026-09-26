.PHONY: all setup run test clean help

VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest

all: setup

setup:
	@echo "==> Setting up Python virtual environment and dependencies..."
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
	fi
	@$(PIP) install --upgrade pip setuptools wheel
	@$(PIP) install -r requirements-dev.txt
	@$(PIP) install -e .
	@if [ ! -f .env ] && [ -f .env.example ]; then \
		cp .env.example .env; \
		echo "==> Created .env from .env.example (set AI_API_KEY for live execution)"; \
	fi
	@echo "==> Setup completed successfully."

run:
	@if [ ! -d "$(VENV)" ]; then \
		echo "==> Virtual environment not found. Running make setup first..."; \
		$(MAKE) setup; \
	fi
	@echo "==> Launching AI Coding Harness FastAPI Backend..."
	@$(PYTHON) -m uvicorn harness.api.server:app --host 0.0.0.0 --port 8000 --reload

test:
	@if [ ! -d "$(VENV)" ]; then \
		echo "==> Virtual environment not found. Running make setup first..."; \
		$(MAKE) setup; \
	fi
	@echo "==> Running automated test suite..."
	@$(PYTHON) -m pytest tests/ -v

clean:
	@echo "==> Cleaning build artifacts, caches, and virtual environment..."
	@rm -rf $(VENV)
	@rm -rf build/ dist/ *.egg-info/ .eggs/
	@rm -rf .pytest_cache/ .coverage coverage.xml htmlcov/
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*~" -delete
	@echo "==> Clean completed."

help:
	@echo "AI Coding Harness - Available Commands:"
	@echo "  make setup   - Create virtual environment and install all dependencies"
	@echo "  make run     - Start FastAPI backend server on http://0.0.0.0:8000"
	@echo "  make test    - Execute automated test suite"
	@echo "  make clean   - Remove virtualenv, cache, and temporary build files"
