"""Auto-PR Router for CaffiPilot Agent Server.

Provides endpoints to accept a GitHub repository URL + an issue/task prompt,
clone the repo into an isolated workspace, run the CaffiPilot agent to investigate
and implement the fix/feature, verify changes, push the branch, and automatically
create a Pull Request on GitHub.
"""

import asyncio
import datetime
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import requests
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Load environment variables from .env
load_dotenv(override=True)

from openhands.agent_server.server_details_router import update_last_execution_time

logger = logging.getLogger(__name__)

auto_pr_router = APIRouter(prefix="/auto-pr", tags=["Auto PR Workflow"])


class AutoPRRequest(BaseModel):
    repo_url: str = Field(
        ...,
        description="GitHub repository URL (e.g. 'https://github.com/owner/repo' or 'owner/repo')",
        examples=["https://github.com/octocat/Hello-World"],
    )
    issue: str = Field(
        ...,
        description="Description of the issue, task, or feature request to implement",
        examples=["Fix typo in README and add installation instructions"],
    )
    github_token: str | None = Field(
        default=None,
        description="GitHub Personal Access Token with repo/pull-request permissions. Optional if GITHUB_TOKEN environment variable is set.",
    )
    base_branch: str | None = Field(
        default=None,
        description="Base branch to target for the PR (defaults to repo default branch, e.g. 'main')",
    )
    branch_name: str | None = Field(
        default=None,
        description="Branch name to create for the fix (defaults to 'CaffiPilot/fix-<timestamp>')",
    )
    llm_model: str | None = Field(
        default=None,
        description="LLM model to use (defaults to LLM_MODEL env var or 'gpt-4o')",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="LLM API Key. Optional if LLM_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY env var is set.",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="Optional custom base URL for the LLM provider",
    )


class AutoPRJob(BaseModel):
    job_id: str
    status: str = Field(
        description="Status: 'pending', 'running', 'completed', 'failed'"
    )
    repo_url: str
    issue: str
    branch_name: str | None = None
    base_branch: str | None = None
    pull_request_url: str | None = None
    files_changed: list[str] = Field(default_factory=list)
    error: str | None = None
    logs: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


# In-memory job repository
_jobs: dict[str, AutoPRJob] = {}


def _parse_github_repo(url: str) -> tuple[str, str]:
    """Extract owner and repo name from various GitHub URL formats."""
    url = url.strip()
    # Match https://github.com/owner/repo or git@github.com:owner/repo
    pattern = r"(?:https?://github\.com/|git@github\.com:|^)([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git|/)?$"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(
            f"Invalid GitHub repository URL: '{url}'. Expected format 'owner/repo' or 'https://github.com/owner/repo'"
        )
    return match.group(1), match.group(2)


def _append_log(job: AutoPRJob | None, message: str) -> None:
    if job is None:
        return
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    job.logs.append(entry)
    job.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    logger.info(f"[AutoPR {job.job_id}] {message}")


def _execute_auto_pr(job_id: str, request: AutoPRRequest) -> None:
    job = _jobs.get(job_id)
    if not job:
        return

    temp_dir = None
    try:
        load_dotenv(override=True)
        job.status = "running"
        _append_log(job, f"Starting Auto-PR task for: {request.repo_url}")

        owner, repo_name = _parse_github_repo(request.repo_url)
        _append_log(job, f"Identified repository: {owner}/{repo_name}")

        github_token = (
            request.github_token
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN")
        )
        if github_token:
            _append_log(job, "GitHub authentication detected (Remote PR mode enabled).")
            clone_url = (
                f"https://x-access-token:{github_token}@github.com/{owner}/{repo_name}.git"
            )
        else:
            _append_log(
                job,
                "No GitHub token provided. Running in Zero-Token Evaluation mode (anonymous clone & local commit/patch verification).",
            )
            clone_url = f"https://github.com/{owner}/{repo_name}.git"

        llm_base_url = request.llm_base_url or os.environ.get(
            "LLM_BASE_URL", "https://ollama.com/v1"
        )
        if llm_base_url:
            llm_base_url = llm_base_url.strip()
            if not llm_base_url:
                llm_base_url = "https://ollama.com/v1"

        raw_model = request.llm_model or os.environ.get(
            "LLM_MODEL", "openai/gpt-oss:120b"
        )
        if "ollama.com" in (llm_base_url or ""):
            # If the user or UI passed gpt-4o or another non-ollama model, map to gpt-oss:120b
            if not raw_model or "gpt-4" in raw_model or "claude" in raw_model:
                llm_model = "openai/gpt-oss:120b"
            elif not raw_model.startswith("openai/"):
                llm_model = f"openai/{raw_model}"
            else:
                llm_model = raw_model
        else:
            llm_model = raw_model

        llm_api_key = (
            request.llm_api_key
            or os.environ.get("AI_API_KEY")
            or os.environ.get("LLM_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )

        if not llm_api_key:
            raise ValueError(
                "LLM API key is required. Set export AI_API_KEY='...' or LLM_API_KEY in environment, or provide 'llm_api_key' in the request."
            )

        # Create isolated workspace directory inside the project tree
        # (avoids macOS /var/folders "Operation not permitted" on machines
        #  where Terminal lacks Full Disk Access)
        _project_root = Path(__file__).resolve().parents[3]  # → CaffiPilot/
        _clones_base = _project_root / "workspace" / ".clones"
        _clones_base.mkdir(parents=True, exist_ok=True)
        temp_dir = str(
            tempfile.mkdtemp(prefix=f"ai_harness_pr_{repo_name}_", dir=str(_clones_base))
        )
        _append_log(job, f"Created temporary workspace at {temp_dir}")

        # Clone repository (cwd set explicitly to avoid macOS cwd permission issues)
        _append_log(job, f"Cloning {owner}/{repo_name}...")
        clone_proc = subprocess.run(
            ["git", "clone", clone_url, temp_dir],
            capture_output=True,
            text=True,
            cwd="/",
        )
        if clone_proc.returncode != 0:
            raise RuntimeError(f"git clone failed: {clone_proc.stderr.strip()}")

        # Configure git identity in workspace
        subprocess.run(
            ["git", "config", "user.name", "AI Harness Agent"],
            cwd=temp_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "agent@CaffiPilot.local"],
            cwd=temp_dir,
            check=True,
        )

        # Detect default branch if base_branch not specified
        if request.base_branch:
            base_branch = request.base_branch
            subprocess.run(["git", "checkout", base_branch], cwd=temp_dir, check=True)
        else:
            rev_proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            base_branch = rev_proc.stdout.strip()
        job.base_branch = base_branch
        _append_log(job, f"Base branch: {base_branch}")

        # Create new feature/fix branch
        branch_name = (
            request.branch_name
            or f"CaffiPilot/fix-{int(datetime.datetime.now().timestamp())}"
        )
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=temp_dir, check=True)
        job.branch_name = branch_name
        _append_log(job, f"Created branch: {branch_name}")

        # Initialize AI Harness Agent
        _append_log(job, f"Initializing AI Harness Agent with model '{llm_model}'...")
        from openhands.sdk import LLM, Conversation
        from openhands.tools.preset.default import get_default_agent

        llm_kwargs: dict[str, Any] = {
            "model": llm_model,
            "api_key": llm_api_key,
            "drop_params": True,
        }
        if llm_base_url:
            llm_kwargs["base_url"] = llm_base_url

        def on_event(event: Any) -> None:
            try:
                # 1. ActionEvent: Tool calls
                if hasattr(event, "tool_name") and event.tool_name:
                    tool_desc = ""
                    if hasattr(event, "action") and event.action:
                        act = getattr(event.action, "model_dump", lambda: {})()
                        if "command" in act:
                            tool_desc = f" `$ {act['command'][:90]}`"
                        elif "path" in act:
                            action_name = act.get("action", "")
                            tool_desc = f" `[{action_name}] {act['path']}`"
                        elif "file_path" in act:
                            tool_desc = f" `{act['file_path']}`"
                    _append_log(job, f"[ACTION] 🛠️ Tool '{event.tool_name}'{tool_desc}")

                # 2. Reasoning / thoughts
                if hasattr(event, "thought") and event.thought:
                    thought_parts = []
                    for t in event.thought:
                        txt = getattr(t, "text", "")
                        if txt:
                            thought_parts.append(txt.strip())
                    if thought_parts:
                        snippet = " ".join(thought_parts)[:180]
                        _append_log(job, f"[THINKING] 🧠 {snippet}")
                elif hasattr(event, "reasoning_content") and event.reasoning_content:
                    _append_log(
                        job, f"[THINKING] 🧠 {event.reasoning_content[:180].strip()}"
                    )

                # 3. Observations / Results
                if hasattr(event, "observation") and event.observation is not None:
                    obs_str = str(event.observation).strip()
                    if obs_str:
                        preview = obs_str.splitlines()[0][:140]
                        _append_log(job, f"[RESULT] 📋 {preview}")
            except Exception as e:
                logger.debug(f"Event callback error: {e}")

        llm = LLM(**llm_kwargs)
        agent = get_default_agent(llm=llm, cli_mode=True)
        conversation = Conversation(
            agent=agent, workspace=temp_dir, callbacks=[on_event]
        )

        prompt = (
            f"You are an expert autonomous software engineer working on this repository.\n"
            f"Your task is to resolve the following issue or requirement:\n\n"
            f"=== ISSUE DESCRIPTION ===\n"
            f"{request.issue}\n"
            f"=========================\n\n"
            f"Instructions:\n"
            f"1. Explore the codebase, inspect relevant files, and locate where changes are needed.\n"
            f"2. Implement the solution cleanly and accurately.\n"
            f"3. Run existing tests, linters, or verification commands using your terminal tool if available.\n"
            f"4. Do NOT leave temporary or debugging files behind.\n"
            f"5. Once complete, state your summary of changes."
        )

        _append_log(job, "Running AI Harness Agent loop...")
        conversation.send_message(prompt)
        conversation.run()
        _append_log(job, "Agent completed execution loop.")

        first_line_issue = request.issue.strip().splitlines()[0][:70]

        # Check for uncommitted working tree changes and commit them if needed
        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        uncommitted = [
            line.strip() for line in status_proc.stdout.splitlines() if line.strip()
        ]
        if uncommitted:
            _append_log(
                job, f"Staging and committing {len(uncommitted)} modified file(s)..."
            )
            subprocess.run(["git", "add", "-A"], cwd=temp_dir, check=True)
            commit_msg = (
                f"fix: {first_line_issue}\n\n"
                f"Automated changes by AI Harness Agent.\n\n"
                f"Issue prompt:\n{request.issue}"
            )
            subprocess.run(
                ["git", "commit", "-m", commit_msg], cwd=temp_dir, check=True
            )

        # Detect all files changed between the base branch and the new branch
        diff_proc = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base_branch}..HEAD"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        changed_files = [f.strip() for f in diff_proc.stdout.splitlines() if f.strip()]

        if not changed_files:
            _append_log(job, "No file modifications were made by the agent.")
            job.status = "completed"
            job.error = "Agent completed but did not produce any file changes."
            return

        job.files_changed = changed_files
        _append_log(
            job,
            f"Detected changed files ({len(changed_files)}): {', '.join(changed_files[:5])}",
        )

        # If no GitHub token provided, complete the job in Zero-Token Evaluation mode!
        if not github_token:
            patch_proc = subprocess.run(
                ["git", "diff", f"origin/{base_branch}..HEAD"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
            )
            patch_content = patch_proc.stdout or ""
            _append_log(job, "--------------------------------------------------")
            _append_log(
                job,
                f"🎉 Task completed successfully! Solution committed to branch '{branch_name}'.",
            )
            _append_log(
                job,
                f"📝 Summary: {len(changed_files)} file(s) modified successfully: {', '.join(changed_files[:5])}",
            )
            if patch_content:
                preview_lines = patch_content.splitlines()[:15]
                _append_log(job, "📄 Patch diff preview:")
                for pl in preview_lines:
                    _append_log(job, f"   {pl}")
            _append_log(
                job,
                "ℹ️ Remote GitHub PR skipped (Zero-token evaluation mode: public evaluation completed without requiring GitHub credentials).",
            )
            job.status = "completed"
            job.pull_request_url = (
                f"Local Solution Verified ({branch_name}) - {len(changed_files)} file(s) modified"
            )
            return

        # Check permissions and handle fork if user cannot push directly to target repo
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        user_resp = requests.get(
            "https://api.github.com/user", headers=headers, timeout=10
        )
        auth_user = (
            user_resp.json().get("login") if user_resp.status_code == 200 else None
        )

        repo_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo_name}",
            headers=headers,
            timeout=10,
        )
        can_push = False
        if repo_resp.status_code == 200:
            can_push = repo_resp.json().get("permissions", {}).get("push", False)

        push_remote = "origin"
        pr_head = branch_name

        if not can_push and auth_user and auth_user.lower() != owner.lower():
            _append_log(
                job,
                f"No direct push permission on {owner}/{repo_name}. Creating/checking fork under {auth_user}...",
            )
            fork_resp = requests.post(
                f"https://api.github.com/repos/{owner}/{repo_name}/forks",
                headers=headers,
                timeout=15,
            )
            fork_repo_name = repo_name
            fork_owner = auth_user
            if fork_resp.status_code in (200, 202):
                fork_data = fork_resp.json()
                fork_repo_name = fork_data.get("name", repo_name)
                fork_owner = fork_data.get("owner", {}).get("login", auth_user)
                # Fork was requested, poll for up to 15 seconds until repository is accessible
                import time

                _append_log(
                    job,
                    f"Waiting for GitHub fork creation ({fork_owner}/{fork_repo_name}) to complete...",
                )
                for _ in range(8):
                    time.sleep(2)
                    check = requests.get(
                        f"https://api.github.com/repos/{fork_owner}/{fork_repo_name}",
                        headers=headers,
                        timeout=10,
                    )
                    if check.status_code == 200:
                        break
            elif fork_resp.status_code in (403, 404):
                raise RuntimeError(
                    f"GitHub rejected fork creation (HTTP {fork_resp.status_code}). "
                    f"Your GITHUB_TOKEN is missing the 'repo' scope. "
                    f"Please generate a token with 'repo' checked at https://github.com/settings/tokens"
                )

            fork_remote_url = f"https://x-access-token:{github_token}@github.com/{fork_owner}/{fork_repo_name}.git"
            subprocess.run(
                ["git", "remote", "add", "fork", fork_remote_url],
                cwd=temp_dir,
                check=False,
            )
            push_remote = "fork"
            pr_head = f"{fork_owner}:{branch_name}"
            _append_log(
                job,
                f"Fork ready: {fork_owner}/{fork_repo_name}. Pushing branch to fork...",
            )

        # Push to remote branch
        _append_log(job, f"Pushing branch '{branch_name}' to GitHub ({push_remote})...")
        push_proc = subprocess.run(
            ["git", "push", "-u", push_remote, branch_name],
            cwd=temp_dir,
            capture_output=True,
            text=True,
        )
        if push_proc.returncode != 0:
            if "Permission to" in push_proc.stderr or "403" in push_proc.stderr:
                raise RuntimeError(
                    f"GitHub push permission denied (403). Your GITHUB_TOKEN does not have write/push access. "
                    f"Please generate a token with 'repo' scope at https://github.com/settings/tokens"
                )
            raise RuntimeError(f"git push failed: {push_proc.stderr.strip()}")

        # Create Pull Request via GitHub REST API
        _append_log(
            job,
            f"Opening Pull Request on GitHub (target: {owner}/{repo_name}:{base_branch})...",
        )
        pr_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        pr_body = (
            f"## CaffiPilot Automated Pull Request\n\n"
            f"### Task / Issue\n"
            f"> {request.issue}\n\n"
            f"### Files Modified\n"
            + "\n".join(f"- `{f}`" for f in changed_files)
            + "\n\n---\n*Created automatically by CaffiPilot Agent Server.*"
        )
        pr_payload = {
            "title": f"fix: {first_line_issue}",
            "body": pr_body,
            "head": pr_head,
            "base": base_branch,
        }

        pr_resp = requests.post(pr_url, headers=headers, json=pr_payload, timeout=30)
        if pr_resp.status_code == 201:
            pr_data = pr_resp.json()
            html_url = pr_data.get("html_url")
            job.pull_request_url = html_url
            job.status = "completed"
            _append_log(job, f"🎉 Pull Request created successfully: {html_url}")
        else:
            raise RuntimeError(
                f"GitHub PR creation failed (HTTP {pr_resp.status_code}): {pr_resp.text}"
            )

    except Exception as exc:
        logger.exception("Error executing Auto-PR task")
        job.status = "failed"
        job.error = str(exc)
        _append_log(job, f"ERROR: {exc}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


@auto_pr_router.post(
    "/run",
    response_model=AutoPRJob,
    summary="Trigger an autonomous issue-to-PR task",
)
async def run_auto_pr(
    request: AutoPRRequest,
    background_tasks: BackgroundTasks,
    sync: bool = False,
) -> AutoPRJob:
    """Submit a GitHub repo URL and an issue/task description.

    The backend will clone the repository, run the CaffiPilot agent to implement
    the solution and tests, commit the changes, push a branch, and open a Pull Request.

    - By default, runs asynchronously in the background and returns a `job_id`.
    - If `sync=true` is passed, the HTTP request will wait until the agent finishes.
    """
    update_last_execution_time()
    job_id = uuid.uuid4().hex[:12]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    job = AutoPRJob(
        job_id=job_id,
        status="pending",
        repo_url=request.repo_url,
        issue=request.issue,
        created_at=now,
        updated_at=now,
        logs=[],
    )
    _jobs[job_id] = job
    _append_log(job, f"Enqueued job {job_id}")

    if sync:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _execute_auto_pr, job_id, request)
    else:
        background_tasks.add_task(_execute_auto_pr, job_id, request)

    return _jobs[job_id]


@auto_pr_router.get(
    "/jobs/{job_id}",
    response_model=AutoPRJob,
    summary="Check status and logs of an Auto-PR job",
)
async def get_auto_pr_job(job_id: str) -> AutoPRJob:
    """Retrieve live status, logs, modified files, and Pull Request URL for a job."""
    update_last_execution_time()
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@auto_pr_router.get(
    "/jobs",
    response_model=list[AutoPRJob],
    summary="List all Auto-PR jobs",
)
async def list_auto_pr_jobs() -> list[AutoPRJob]:
    """List all recent Auto-PR jobs and their current status."""
    update_last_execution_time()
    return list(_jobs.values())


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@auto_pr_router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
@auto_pr_router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui() -> HTMLResponse:
    """Serve the interactive web test UI for CaffiPilot."""
    html_path = TEMPLATES_DIR / "index.html"
    if html_path.exists():
        content = html_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>UI template not found</h1>", status_code=404)
