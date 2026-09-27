#!/usr/bin/env python3
"""CaffiPilot Hackathon 2026 - Standardised CLI/TUI Runner.

Provides a unified execution entry point for 'make run':
- Reads AI_API_KEY from environment or .env
- Launches or verifies the CaffiPilot server and Web Cockpit
- Supports both interactive terminal TUI and automated evaluation script arguments
"""

import argparse
import os
import sys
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv(override=False)

API_BASE = os.environ.get("HARNESS_API_BASE", "http://127.0.0.1:8000")


def print_banner() -> None:
    print("\033[36m" + "=" * 74 + "\033[0m")
    print(
        "\033[1;35m  AI HARNESS HACKATHON 2026\033[0m - \033[1;32mAutonomous Agent Evaluation Environment\033[0m"
    )
    print("\033[36m" + "=" * 74 + "\033[0m")
    model = os.environ.get("LLM_MODEL", "openai/gpt-oss:120b")
    base_url = os.environ.get("LLM_BASE_URL", "https://ollama.com/v1")
    print(f" \033[33m•\033[0m Text Model  : \033[1m{model}\033[0m")
    print(f" \033[33m•\033[0m LLM Endpoint: \033[1m{base_url}\033[0m")

    api_key = os.environ.get("AI_API_KEY") or os.environ.get("LLM_API_KEY")
    if api_key:
        masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f" \033[33m•\033[0m API Key     : \033[32mConfigured ({masked})\033[0m")
    else:
        print(
            f" \033[33m•\033[0m API Key     : \033[31mNot Set (Provide via AI_API_KEY)\033[0m"
        )

    gh_token = os.environ.get("GITHUB_TOKEN")
    if gh_token:
        print(f" \033[33m•\033[0m GitHub Mode : \033[32mRemote PR Enabled (Token Detected)\033[0m")
    else:
        print(
            f" \033[33m•\033[0m GitHub Mode : \033[32mZero-Token Evaluation (No token needed)\033[0m"
        )
    print("\033[36m" + "-" * 74 + "\033[0m")


def wait_for_server(timeout: int = 15) -> bool:
    """Check if server is responding or wait for it to boot."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{API_BASE}/alive", timeout=1.5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def run_task(repo_url: str, issue: str, base_branch: str | None = None) -> int:
    """Execute an autonomous issue-to-PR task and stream logs to stdout."""
    api_key = os.environ.get("AI_API_KEY") or os.environ.get("LLM_API_KEY")
    gh_token = os.environ.get("GITHUB_TOKEN")
    model = os.environ.get("LLM_MODEL", "openai/gpt-oss:120b")

    print(f"\n\033[1;34m[CaffiPilot]\033[0m Submitting task to harness...")
    print(f" \033[36mRepository:\033[0m {repo_url}")
    print(f" \033[36mTask / Issue:\033[0m {issue}\n")

    payload = {
        "repo_url": repo_url,
        "issue": issue,
        "llm_api_key": api_key,
        "github_token": gh_token,
        "llm_model": model,
        "base_branch": base_branch or None,
    }

    try:
        resp = requests.post(f"{API_BASE}/api/auto-pr/run", json=payload, timeout=20)
        if resp.status_code != 200:
            print(
                f"\033[31m[ERROR] Failed to start task ({resp.status_code}): {resp.text}\033[0m"
            )
            return 1

        job = resp.json()
        job_id = job.get("job_id")
        print(f"\033[32m✔ Job enqueued successfully: {job_id}\033[0m")
        print("\033[33m--- Beginning Live Execution Log Stream ---\033[0m\n")

        seen_logs = 0
        while True:
            time.sleep(1)
            try:
                status_resp = requests.get(
                    f"{API_BASE}/api/auto-pr/jobs/{job_id}", timeout=10
                )
                if status_resp.status_code != 200:
                    continue
                job_data = status_resp.json()
                logs = job_data.get("logs", [])

                # Print new logs
                if len(logs) > seen_logs:
                    for i in range(seen_logs, len(logs)):
                        log_line = logs[i]
                        # Colorize terminal line
                        if "[THINKING]" in log_line:
                            print(f"\033[35m{log_line}\033[0m")
                        elif "[ACTION]" in log_line:
                            print(f"\033[36m{log_line}\033[0m")
                        elif "[RESULT]" in log_line:
                            print(f"\033[90m{log_line}\033[0m")
                        elif "🎉" in log_line or "success" in log_line.lower():
                            print(f"\033[1;32m{log_line}\033[0m")
                        elif "ERROR" in log_line or "failed" in log_line.lower():
                            print(f"\033[1;31m{log_line}\033[0m")
                        else:
                            print(log_line)
                    seen_logs = len(logs)

                status = job_data.get("status")
                if status in ("completed", "failed"):
                    print("\033[33m-------------------------------------------\033[0m")
                    if status == "completed":
                        pr_url = job_data.get("pull_request_url")
                        print(f"\n\033[1;32m🎉 TASK COMPLETED SUCCESSFULLY!\033[0m")
                        if pr_url:
                            if "http" in pr_url:
                                print(
                                    f"\033[1;36mPull Request URL:\033[0m \033[4;32m{pr_url}\033[0m\n"
                                )
                            else:
                                print(
                                    f"\033[1;36mSolution Verification:\033[0m \033[32m{pr_url}\033[0m\n"
                                )
                        return 0
                    else:
                        print(
                            f"\n\033[1;31m❌ Task failed: {job_data.get('error')}\033[0m\n"
                        )
                        return 1
            except Exception as poll_err:
                print(f"[Warn] Polling connection hiccup: {poll_err}")
    except Exception as e:
        print(f"\033[31m[ERROR] Connection to AI Harness backend failed: {e}\033[0m")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CaffiPilot Hackathon 2026 Evaluation Runner"
    )
    parser.add_argument(
        "--repo", type=str, help="Target GitHub repository URL for evaluation"
    )
    parser.add_argument(
        "--issue", type=str, help="Evaluation issue or task description"
    )
    parser.add_argument("--base-branch", type=str, default=None, help="Base branch")
    parser.add_argument(
        "--api-key",
        "--api_key",
        dest="api_key",
        type=str,
        default=None,
        help="API key for LLM provider (Ollama Cloud / Hackathon key)",
    )
    parser.add_argument(
        "--serve-only",
        action="store_true",
        help="Keep server running without interactive prompt",
    )
    args, _ = parser.parse_known_args()

    if args.api_key:
        os.environ["AI_API_KEY"] = args.api_key.strip()
        os.environ["LLM_API_KEY"] = args.api_key.strip()

    print_banner()

    # Ensure backend is online
    print("Checking CaffiPilot server status...")
    if not wait_for_server(timeout=3):
        print("\033[33mStarting CaffiPilot agent-server daemon...\033[0m")
        import subprocess

        # Start server as subprocess
        env = os.environ.copy()
        env["PATH"] = f"{os.path.expanduser('~')}/.local/bin:{env.get('PATH', '')}"
        subprocess.Popen(
            ["uv", "run", "agent-server", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(Path(__file__).resolve().parent),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_server(timeout=15):
            print(
                "\033[31mFailed to start CaffiPilot agent-server. Check uv and dependencies.\033[0m"
            )
            sys.exit(1)

    print(f"\033[32m✔ CaffiPilot Backend Online:\033[0m {API_BASE}")
    print(f"\033[32m✔ Web Cockpit Dashboard    :\033[0m {API_BASE}/ui\n")

    # If automated args provided
    if args.repo and args.issue:
        sys.exit(run_task(args.repo, args.issue, args.base_branch))

    if args.serve_only:
        print("\033[32mCaffiPilot is running in evaluation server mode.\033[0m")
        print("Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down.")
            sys.exit(0)

    # Interactive Terminal User Interface (TUI)
    print("\033[1mTerminal Evaluation Interface (TUI)\033[0m")
    print(
        "Enter the test parameters, or press Enter to keep server running for Web UI."
    )
    print("-" * 74)

    try:
        repo_input = input(
            "\033[36mTarget GitHub Repo URL\033[0m [default: https://github.com/adityamathur5934/GitLearning]: "
        ).strip()
        if not repo_input:
            repo_input = "https://github.com/adityamathur5934/GitLearning"

        issue_input = input(
            "\033[36mEvaluation Issue / Task\033[0m [or press Enter to run Web Server mode]: "
        ).strip()
        if not issue_input:
            print(
                f"\n\033[32mServer is running at {API_BASE}/ui. Send requests via Web UI or HTTP POST.\033[0m"
            )
            print("Press Ctrl+C to stop.")
            while True:
                time.sleep(1)

        sys.exit(run_task(repo_input, issue_input))
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
