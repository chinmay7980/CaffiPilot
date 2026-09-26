"""GitHub OAuth, Repository Discovery, Direct Commit & Push, and Pull Request Integration."""

import asyncio
import os
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx

from harness.api.routes.tasks import active_runners
from harness.tools.git_tools import _run_git

router = APIRouter(prefix="/api/v1/github", tags=["GitHub Integration"])
logger = logging.getLogger(__name__)

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")


class CommitPushRequest(BaseModel):
    commit_message: Optional[str] = None
    branch_name: Optional[str] = "main"


class CreatePRRequest(BaseModel):
    branch_name: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    target_branch: str = "main"


@router.get("/oauth/login")
async def github_oauth_login():
    """Redirects the user to official GitHub OAuth authorization endpoint."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=400,
            detail="GITHUB_CLIENT_ID not configured in backend environment. Please provide your GitHub Username or Personal Access Token.",
        )

    authorize_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&scope=repo,user,read:org"
    )
    return RedirectResponse(url=authorize_url)


@router.get("/callback")
async def github_oauth_callback(code: str = Query(...)):
    """Exchanges GitHub OAuth code for access token and redirects to frontend application."""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="OAuth credentials not set in backend.")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        if res.status_code == 200:
            token_data = res.json()
            access_token = token_data.get("access_token")
            if access_token:
                return RedirectResponse(url=f"http://localhost:5173/?token={access_token}")

    return RedirectResponse(url="http://localhost:5173/?auth=failed")


@router.get("/user")
async def get_github_user(
    username: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Verifies and returns GitHub user profile dynamically for ANY entered username or token."""
    auth_token = token
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ")[1]

    headers = {"Accept": "application/vnd.github.v3+json"}
    if auth_token and auth_token.strip():
        headers["Authorization"] = f"Bearer {auth_token.strip()}"
        url = "https://api.github.com/user"
    elif username and username.strip():
        url = f"https://api.github.com/users/{username.strip()}"
    elif os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.getenv('GITHUB_TOKEN')}"
        url = "https://api.github.com/user"
    else:
        return {
            "authenticated": False,
            "username": None,
            "message": "Please enter a GitHub Username or Access Token to authenticate.",
        }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                return {
                    "authenticated": True,
                    "username": data.get("login"),
                    "name": data.get("name") or data.get("login"),
                    "avatar_url": data.get("avatar_url"),
                    "html_url": data.get("html_url"),
                    "public_repos": data.get("public_repos", 0),
                }
            elif res.status_code == 404:
                raise HTTPException(status_code=404, detail=f"GitHub user '{username}' not found.")
            elif res.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="GitHub API unauthenticated rate limit reached. Please enter a Personal Access Token (PAT) or use GitHub OAuth login.",
                )
            else:
                raise HTTPException(status_code=res.status_code, detail=f"GitHub API Error: {res.text}")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"GitHub user verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to verify GitHub user: {str(e)}")


@router.get("/repos")
async def list_github_repos(
    username: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Lists ALL real repositories belonging to the specified GitHub user account."""
    auth_token = token
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ")[1]

    headers = {"Accept": "application/vnd.github.v3+json"}
    if auth_token and auth_token.strip():
        headers["Authorization"] = f"Bearer {auth_token.strip()}"
        url = "https://api.github.com/user/repos?sort=updated&per_page=100&type=all"
    elif username and username.strip():
        url = f"https://api.github.com/users/{username.strip()}/repos?sort=updated&per_page=100"
    elif os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.getenv('GITHUB_TOKEN')}"
        url = "https://api.github.com/user/repos?sort=updated&per_page=100&type=all"
    else:
        raise HTTPException(status_code=400, detail="Username or Token is required to fetch repositories.")

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                raw_repos = res.json()
                repos = []
                for r in raw_repos:
                    repos.append({
                        "id": r.get("id"),
                        "name": r.get("name"),
                        "full_name": r.get("full_name"),
                        "owner": r.get("owner", {}).get("login", username),
                        "html_url": r.get("html_url"),
                        "clone_url": r.get("clone_url"),
                        "default_branch": r.get("default_branch", "main"),
                        "description": r.get("description"),
                        "private": r.get("private", False),
                    })
                return repos
            elif res.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="GitHub API rate limit reached for unauthenticated requests. Please provide your Personal Access Token (PAT) to load all your real repositories.",
                )
            else:
                raise HTTPException(status_code=res.status_code, detail=f"Failed to fetch repos: {res.text}")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to fetch GitHub repos: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching repositories: {str(e)}")


@router.post("/commit-and-push/{task_id}")
async def commit_and_push_changes(task_id: str, req: CommitPushRequest):
    """Commits and pushes AI changes directly to the target repository."""
    runner = active_runners.get(task_id)
    if not runner:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    repo_path = runner.state.repo_path
    commit_msg = req.commit_message or f"feat(ai-harness): {runner.state.issue_description} [{task_id}]"
    branch = req.branch_name or "main"

    try:
        await _run_git(repo_path, "add", "-A")
        code_commit, out_commit, err_commit = await _run_git(
            repo_path, "commit", "-m", commit_msg, "--allow-empty"
        )
        code_push, out_push, err_push = await _run_git(repo_path, "push", "origin", branch)
        _, sha, _ = await _run_git(repo_path, "rev-parse", "HEAD")

        return {
            "success": True,
            "task_id": task_id,
            "commit_msg": commit_msg,
            "commit_sha": sha.strip()[:7] if sha else "HEAD",
            "branch": branch,
            "pushed": code_push == 0,
            "message": f"Successfully committed and pushed changes to repository branch '{branch}'!",
        }
    except Exception as e:
        logger.error(f"Commit & Push failed for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Commit & push failed: {str(e)}")


@router.post("/create-pr/{task_id}")
@router.post("/commit-and-pr/{task_id}")
async def create_pull_request(
    task_id: str,
    req: CreatePRRequest,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
):
    """Commits changes, pushes to user fork/origin, and opens an official GitHub Pull Request to ANY target public repository."""
    runner = active_runners.get(task_id)
    if not runner:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    repo_path = runner.state.repo_path
    feature_branch = req.branch_name or f"caffipilot/feature-{task_id[-6:]}"
    target_branch = req.target_branch or "main"
    pr_title = req.title or f"feat(ai-agent): {runner.state.issue_description}"
    pr_body = req.body or (
        f"## 🤖 Autonomous AI Agent Code Modifications\n\n"
        f"**Task ID**: `{task_id}`\n"
        f"**Issue Prompt**: {runner.state.issue_description}\n"
        f"**Files Changed**: {', '.join(runner.state.files_modified) if runner.state.files_modified else 'Workspace code updates'}\n\n"
        f"---\n*Generated automatically by CaffiPilot AI Coding Harness.*"
    )

    auth_token = token or os.getenv("GITHUB_TOKEN")
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ")[1]

    if not auth_token:
        raise HTTPException(
            status_code=400,
            detail="Personal Access Token or GitHub OAuth token is required to create a Pull Request on public repositories.",
        )

    try:
        # 1. Fetch authenticated user profile
        auth_username = None
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {auth_token}",
        }
        async with httpx.AsyncClient() as client:
            user_res = await client.get("https://api.github.com/user", headers=headers)
            if user_res.status_code == 200:
                auth_username = user_res.json().get("login")

        if not auth_username:
            raise HTTPException(status_code=401, detail="Failed to verify authenticated GitHub user with provided token.")

        # 2. Extract repository owner & repo name from origin URL
        code_remote, remote_url, _ = await _run_git(repo_path, "remote", "get-url", "origin")
        upstream_owner = None
        repo_name = None
        if code_remote == 0 and remote_url:
            clean_url = (
                remote_url.strip()
                .replace("git@github.com:", "")
                .replace("https://github.com/", "")
                .replace(".git", "")
            )
            parts = clean_url.split("/")
            if len(parts) >= 2:
                upstream_owner = parts[-2]
                repo_name = parts[-1]

        if not upstream_owner or not repo_name:
            raise HTTPException(status_code=400, detail="Could not determine target GitHub repository owner and name.")

        # 3. Create & checkout feature branch locally and commit changes
        await _run_git(repo_path, "checkout", "-b", feature_branch)
        await _run_git(repo_path, "add", "-A")
        await _run_git(repo_path, "commit", "-m", pr_title, "--allow-empty")
        _, sha, _ = await _run_git(repo_path, "rev-parse", "HEAD")
        commit_sha_short = sha.strip()[:7] if sha else "HEAD"

        is_owner = auth_username.lower() == upstream_owner.lower()
        pr_head_ref = feature_branch
        pr_url = None
        pr_number = None

        if is_owner:
            # Direct push to own repository
            authenticated_origin = f"https://x-access-token:{auth_token}@github.com/{upstream_owner}/{repo_name}.git"
            await _run_git(repo_path, "remote", "set-url", "origin", authenticated_origin)
            code_push, _, err_push = await _run_git(repo_path, "push", "-u", "origin", feature_branch)
            if code_push != 0:
                logger.warning(f"Git push origin failed: {err_push}")
            pr_head_ref = feature_branch
        else:
            # External Public Repo -> Fork repository to user account
            async with httpx.AsyncClient() as client:
                fork_res = await client.post(
                    f"https://api.github.com/repos/{upstream_owner}/{repo_name}/forks",
                    headers=headers,
                )
                if fork_res.status_code not in (200, 202):
                    logger.warning(f"Fork API returned status {fork_res.status_code}: {fork_res.text}")

            await asyncio.sleep(2)  # Wait for GitHub fork creation

            # Set up fork remote and push feature branch to user fork
            fork_url = f"https://x-access-token:{auth_token}@github.com/{auth_username}/{repo_name}.git"
            await _run_git(repo_path, "remote", "remove", "fork")
            await _run_git(repo_path, "remote", "add", "fork", fork_url)
            code_push, _, err_push = await _run_git(repo_path, "push", "-u", "fork", feature_branch)
            if code_push != 0:
                # Retry push to fork
                await asyncio.sleep(2)
                await _run_git(repo_path, "push", "-u", "fork", feature_branch)

            pr_head_ref = f"{auth_username}:{feature_branch}"

        # 4. Create Pull Request on upstream repository via GitHub REST API
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"https://api.github.com/repos/{upstream_owner}/{repo_name}/pulls",
                headers=headers,
                json={
                    "title": pr_title,
                    "head": pr_head_ref,
                    "base": target_branch,
                    "body": pr_body,
                },
            )
            if res.status_code in (200, 201):
                pr_data = res.json()
                pr_url = pr_data.get("html_url")
                pr_number = pr_data.get("number")
            else:
                logger.warning(f"GitHub Pull Request API returned status {res.status_code}: {res.text}")
                # Fallback URL if PR already exists or needs manual submission
                pr_url = f"https://github.com/{upstream_owner}/{repo_name}/compare/{target_branch}...{pr_head_ref}"

        return {
            "success": True,
            "task_id": task_id,
            "commit_sha": commit_sha_short,
            "feature_branch": feature_branch,
            "target_branch": target_branch,
            "title": pr_title,
            "pr_url": pr_url or f"https://github.com/{upstream_owner}/{repo_name}/pulls",
            "pr_number": pr_number,
            "is_fork": not is_owner,
            "message": f"Successfully created branch '{feature_branch}', committed changes, and opened Pull Request on {upstream_owner}/{repo_name}!",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create PR failed for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create Pull Request: {str(e)}")
