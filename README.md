# 🚀 CaffiPilot — Autonomous AI Harness

[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Hackathon](https://img.shields.io/badge/AI_Harness_Hackathon-2026-6366F1?style=for-the-badge)](https://github.com)
[![Model](https://img.shields.io/badge/Model-Ollama_Cloud_(gpt--oss:120b)-10B981?style=for-the-badge)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**CaffiPilot** is an enterprise-grade autonomous AI Harness designed for the **AI Harness Hackathon 2026**. It provides an end-to-end autonomous agent workflow capable of ingesting an issue/task prompt, cloning target GitHub repositories into isolated workspaces, inspecting and editing codebases using autonomous tools, running verifications, pushing branches, and creating verified Pull Requests automatically.

---

## 📋 Standardised Makefile Interface

In compliance with the **AI Harness Hackathon 2026 Evaluation Guidelines**, this repository provides a standardized Makefile at the root:

| Command | Purpose |
| :--- | :--- |
| `make setup` | Install and configure all required dependencies (using `uv`) |
| `make run` | Initialise and launch the AI Harness runner |
| `make test` | Execute the team's test/evaluation procedure |
| `make clean` | Remove generated artefacts, caches, and temporary files |

---

## ⚡ Quick Start

### 1. Environment Configuration
Copy `.env.example` to `.env` or set environment variables:
```bash
cp CaffiPilot/.env.example CaffiPilot/.env
```

Key environment variables:
```bash
# Prescribed Hackathon API Key (takes precedence over LLM_API_KEY)
export AI_API_KEY="your-ollama-cloud-api-key"

# GitHub Personal Access Token (with 'repo' scope for Auto-PR creation)
export GITHUB_TOKEN="ghp_your_github_token"

# Optional overrides (defaults to prescribed settings):
export LLM_MODEL="openai/gpt-oss:120b"
export LLM_BASE_URL="https://ollama.com/v1"
```

### 2. Setup Dependencies
```bash
make setup
```

### 3. Run the Evaluation Suite
```bash
make test
```
All tests should pass:
```text
tests/unit/test_harness_evaluation.py::test_harness_imports PASSED
tests/unit/test_harness_evaluation.py::test_model_configuration PASSED
tests/unit/test_harness_evaluation.py::test_api_key_resolution PASSED
```

---

## 🛠️ Execution Modes

### Mode A: Automated CLI Execution (Non-Interactive / Benchmark Mode)
Run directly via the Makefile with target repository and issue arguments:
```bash
make run ARGS="--repo https://github.com/owner/target-repo --issue 'Fix typo in README and add unit test'"
```
Or pass the API key explicitly:
```bash
make run AI_API_KEY="your-api-key" ARGS="--repo owner/repo --issue 'Implement feature X'"
```

### Mode B: Interactive Terminal TUI Mode
Simply run without arguments to enter the interactive terminal wizard:
```bash
make run
```
You will be prompted for:
1. Target GitHub Repository URL
2. Issue / Task Prompt
3. Base Branch (optional, defaults to repository default branch)

### Mode C: Autonomous Web Cockpit
Launch the background agent server and open the Autonomous Cockpit:
```bash
make run ARGS="--serve-only"
```
Then visit:
👉 **[http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui)**

Features available in the Cockpit:
- **1-Click GitHub OAuth**: Connect GitHub seamlessly with real-time authentication badge.
- **Repository Dispatch**: Submit GitHub URL + task prompt.
- **Real-Time Log Stream**: View agent thought process, tool invocations, and command outputs live.
- **Direct PR Links**: Instant link to the created GitHub Pull Request upon completion.

---

## 🧠 Prescribed Model Alignment

CaffiPilot strictly follows the hackathon requirements:
* **Provider**: Ollama Cloud API (`https://ollama.com/v1`)
* **Model**: `openai/gpt-oss:120b` (text-only prescribed model)
* **Auth**: `AI_API_KEY` (automatically forwarded to the LLM client)

---

## 📁 Repository Structure

```text
CaffiPIlot_/
├── Makefile                       # Mandatory root evaluation Makefile
├── README.md                      # This documentation
└── CaffiPilot/                    # Primary project directory
    ├── Makefile                   # Internal target Makefile
    ├── harness_cli.py             # Evaluation CLI and headless test runner
    ├── .env.example               # Environment template
    ├── openhands-agent-server/    # FastAPI Agent Server with Auto-PR & OAuth routers
    ├── openhands-sdk/             # Core autonomous agent SDK & event protocol
    ├── openhands-tools/           # Presets for file editing, terminal, and bash tools
    ├── openhands-workspace/       # Isolated sandbox workspace management
    └── tests/
        └── unit/
            └── test_harness_evaluation.py  # Standardised evaluation test suite
```

---

## 🛡️ License & Submission

Developed for the **AI Harness Hackathon 2026**. Licensed under the [MIT License](file:///Users/chinmaysoni/Desktop/CaffiPIlot_/CaffiPilot/LICENSE).
