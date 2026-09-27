# 🚀 CaffiPilot — Autonomous AI Harness

[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Hackathon](https://img.shields.io/badge/AI_Harness_Hackathon-2026-6366F1?style=for-the-badge)](https://github.com)
[![Model](https://img.shields.io/badge/Model-Ollama_Cloud_(gpt--oss:120b)-10B981?style=for-the-badge)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**CaffiPilot** is an enterprise-grade autonomous AI Harness designed for the **AI Harness Hackathon 2026**. It provides an end-to-end autonomous agent workflow capable of ingesting an issue/task prompt, cloning target GitHub repositories, inspecting and editing codebases using autonomous tools, running verifications, and creating Pull Requests automatically.

---

## ⚡ Quick Start (3 Steps)

### Step 1 — Clone the repository
```bash
git clone https://github.com/chinmay7980/CaffiPilot_Final.git
cd CaffiPilot_Final/CaffiPilot
```

### Step 2 — Install dependencies
```bash
make setup
```
> This will install [uv](https://docs.astral.sh/uv/) (if missing), sync all Python packages, and create a `.env` file from the template.

### Step 3 — Run CaffiPilot
```bash
make run
```
> You'll be prompted to enter a GitHub repo URL and a task/issue — CaffiPilot will autonomously clone, analyze, edit, and commit the fix.

---

## 🔑 GitHub Token Setup (Optional but Recommended)

CaffiPilot works in **two modes** depending on whether a GitHub token is provided:

| | Zero-Token Mode (default) | Full-Token Mode |
| :--- | :--- | :--- |
| **Clone public repos** | ✅ Works | ✅ Works |
| **Clone private repos** | ❌ No access | ✅ Works |
| **Push branches** | ❌ Local only | ✅ Pushes to GitHub |
| **Create Pull Requests** | ❌ Skipped | ✅ Opens PR automatically |
| **Setup required** | None | Token needed (see below) |

### How to Create a GitHub Token

1. Go to **[github.com/settings/tokens](https://github.com/settings/tokens)**
2. Click **"Generate new token (classic)"**
3. Give it a name (e.g., `CaffiPilot`)
4. Select these scopes:
   - ✅ `repo` (full control of private repositories)
5. Click **"Generate token"**
6. **Copy the token** — it starts with `ghp_...`

### How to Set the Token

**Option A — Add it to your `.env` file** (recommended):
```bash
# Open the .env file inside CaffiPilot/
nano .env
```
Add or update this line:
```
GITHUB_TOKEN=ghp_your_token_here
```

**Option B — Export it in your terminal** (temporary, for the current session):
```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

**Option C — No token at all** (zero-token evaluation mode):
Just skip it! CaffiPilot will clone public repos anonymously and verify changes locally without pushing.

---

## 📋 Makefile Commands

| Command | Purpose |
| :--- | :--- |
| `make setup` | Install `uv`, sync dependencies, and create `.env` |
| `make run` | Launch the AI Harness CLI / TUI |
| `make test` | Run the test suite |
| `make clean` | Remove caches, `.venv`, and temporary files |
| `make help` | Show all available commands |

---

## 🛠️ Execution Modes

### Mode A — Interactive TUI (Recommended for demos)
```bash
make run
```
You'll be prompted for:
1. Target GitHub Repository URL
2. Issue / Task description
3. CaffiPilot does the rest autonomously

### Mode B — Automated CLI (for scripting / benchmarks)
```bash
make run ARGS="--repo https://github.com/owner/repo --issue 'Fix the login bug'"
```
Pass the API key explicitly if needed:
```bash
make run AI_API_KEY="your-api-key" ARGS="--repo owner/repo --issue 'Add dark mode'"
```

### Mode C — Web Cockpit Dashboard
```bash
make run ARGS="--serve-only"
```
Then open: 👉 **[http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui)**

Features:
- **1-Click GitHub OAuth** — Connect GitHub seamlessly
- **Repository Dispatch** — Submit repo URL + task prompt
- **Real-Time Log Stream** — Watch the agent think and act live
- **Direct PR Links** — Instant link to created Pull Request

---

## 🔧 Environment Variables

All configuration goes in `.env` (auto-created by `make setup`):

```bash
# ─── Required ───────────────────────────────────────
AI_API_KEY=your-ollama-cloud-api-key

# ─── Optional (for GitHub PR creation) ──────────────
GITHUB_TOKEN=ghp_your_github_token

# ─── Model Config (defaults shown, usually no change needed) ──
LLM_MODEL=openai/gpt-oss:120b
LLM_BASE_URL=https://ollama.com/v1
```

---

## 🧠 Prescribed Model Alignment

CaffiPilot strictly follows the hackathon requirements:
* **Provider**: Ollama Cloud API (`https://ollama.com/v1`)
* **Model**: `openai/gpt-oss:120b` (text-only prescribed model)
* **Auth**: `AI_API_KEY` (automatically forwarded to the LLM client)

---

## 📁 Repository Structure

```text
CaffiPilot_Final/
└── CaffiPilot/
    ├── Makefile                   # All make commands (setup, run, test, clean)
    ├── README.md                  # This file
    ├── harness_cli.py             # CLI runner and interactive TUI
    ├── .env.example               # Environment template
    ├── .env                       # Your local config (git-ignored)
    ├── pyproject.toml             # Python workspace config (uv)
    ├── openhands-agent-server/    # FastAPI server with Auto-PR & OAuth routers
    ├── openhands-sdk/             # Core autonomous agent SDK & event protocol
    ├── openhands-tools/           # File editing, terminal, and bash tools
    ├── openhands-workspace/       # Isolated sandbox workspace management
    ├── workspace/                 # Runtime workspace (cloned repos go here)
    └── tests/                     # Test suite
```

---

## 🧪 Running Tests

```bash
make test
```
Expected output:
```text
tests/unit/test_harness_evaluation.py::test_harness_imports PASSED
tests/unit/test_harness_evaluation.py::test_model_configuration PASSED
tests/unit/test_harness_evaluation.py::test_api_key_resolution PASSED
```

---

## ❓ Troubleshooting

| Problem | Solution |
| :--- | :--- |
| `make: *** No such file or directory` | Make sure you're inside the `CaffiPilot/` directory |
| `uv: command not found` | Run `make setup` — it auto-installs `uv` |
| `git clone failed: Operation not permitted` | Pull the latest code — this is fixed now |
| `GitHub token is required` | Either set `GITHUB_TOKEN` in `.env` or run without it (zero-token mode) |
| Server won't start | Check port 8000 isn't in use: `lsof -i :8000` |

---

## 🛡️ License & Submission

Developed for the **AI Harness Hackathon 2026**. Licensed under the [MIT License](LICENSE).
