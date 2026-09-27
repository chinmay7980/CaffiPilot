"""GitHub OAuth Router for CaffiPilot Agent Server.

Provides endpoints for 1-click GitHub OAuth authentication:
- /api/auth/github/login: Redirects to GitHub authorization page with 'repo' and 'user' scopes.
- /api/auth/github/callback: Handles the OAuth callback, exchanges code for access token,
  updates GITHUB_TOKEN in memory and in .env, and redirects back to the UI.
- /api/auth/github/status: Returns the current GitHub connection and user details.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import requests
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)

github_oauth_router = APIRouter(prefix="/auth/github", tags=["GitHub OAuth"])


def _get_dotenv_path() -> Path:
    candidates = [
        Path("/Users/chinmaysoni/Desktop/CaffiPIlot_/CaffiPilot/.env"),
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


DOTENV_PATH = _get_dotenv_path()


def _save_token_to_dotenv(token: str) -> None:
    """Persist the authenticated GITHUB_TOKEN into the .env file."""
    os.environ["GITHUB_TOKEN"] = token
    try:
        path = _get_dotenv_path()
        if path.exists():
            content = path.read_text(encoding="utf-8")
            if re.search(r"^GITHUB_TOKEN=.*$", content, flags=re.MULTILINE):
                new_content = re.sub(
                    r"^GITHUB_TOKEN=.*$",
                    f"GITHUB_TOKEN={token}",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                new_content = f"GITHUB_TOKEN={token}\n" + content
            path.write_text(new_content, encoding="utf-8")
            logger.info(f"Updated GITHUB_TOKEN in {path}")
    except Exception as exc:
        logger.warning(f"Could not persist GITHUB_TOKEN to .env: {exc}")


@github_oauth_router.get("/login", summary="Initiate GitHub OAuth Flow")
async def github_login(request: Request) -> RedirectResponse:
    """Redirect user to GitHub OAuth authorization page."""
    load_dotenv(DOTENV_PATH, override=True)
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=400,
            detail="GITHUB_CLIENT_ID not configured in .env. Please set GITHUB_CLIENT_ID.",
        )

    # Determine callback URL dynamically or fallback
    host = request.headers.get("host", "127.0.0.1:8000")
    scheme = "https" if request.url.scheme == "https" else "http"
    redirect_uri = f"{scheme}://{host}/api/auth/github/callback"

    scope = "repo,user"
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&scope={scope}"
        f"&redirect_uri={redirect_uri}"
    )
    return RedirectResponse(url=github_auth_url, status_code=302)


@github_oauth_router.get("/callback", summary="GitHub OAuth Callback")
async def github_callback(
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> HTMLResponse:
    """Exchange authorization code for access token and persist it."""
    load_dotenv(DOTENV_PATH, override=True)
    if error:
        detail = error_description or error
        return HTMLResponse(
            f"""<!DOCTYPE html>
<html>
<head><title>GitHub Auth Failed</title></head>
<body style="font-family:sans-serif; background:#0f172a; color:#f8fafc; display:flex; align-items:center; justify-content:center; height:100vh; margin:0;">
  <div style="background:#1e293b; padding:32px; border-radius:12px; border:1px solid #ef4444; text-align:center; max-width:400px;">
    <h2 style="color:#ef4444;">Authorization Failed</h2>
    <p style="color:#94a3b8;">{detail}</p>
    <a href="/ui" style="display:inline-block; margin-top:16px; padding:10px 20px; background:#6366f1; color:white; text-decoration:none; border-radius:8px;">Back to Dashboard</a>
  </div>
</body>
</html>""",
            status_code=400,
        )

    if not code:
        raise HTTPException(
            status_code=400, detail="Missing 'code' parameter from GitHub callback."
        )

    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET not configured in .env",
        )

    # Exchange code for access token
    token_url = "https://github.com/login/oauth/access_token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }
    headers = {"Accept": "application/json"}
    token_resp = requests.post(token_url, json=payload, headers=headers, timeout=15)
    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=token_resp.status_code,
            detail=f"GitHub token exchange failed: {token_resp.text}",
        )

    data = token_resp.json()
    access_token = data.get("access_token")
    if not access_token:
        err = data.get("error_description") or data.get("error") or "Unknown error"
        raise HTTPException(
            status_code=400, detail=f"Failed to obtain access token: {err}"
        )

    # Fetch user info to verify token
    user_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    user_resp = requests.get(
        "https://api.github.com/user", headers=user_headers, timeout=10
    )
    user_login = (
        user_resp.json().get("login", "user")
        if user_resp.status_code == 200
        else "user"
    )

    # Persist the token to environment and .env
    _save_token_to_dotenv(access_token)

    return HTMLResponse(
        f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>GitHub Authorized</title>
  <meta http-equiv="refresh" content="2;url=/ui?auth_success=1&user={user_login}">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #090d16;
      color: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
    }}
    .card {{
      background: #131b2e;
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 36px 48px;
      border-radius: 16px;
      text-align: center;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
    }}
    .icon {{
      font-size: 48px;
      margin-bottom: 16px;
    }}
    h2 {{
      margin: 0 0 8px 0;
      color: #10b981;
      font-size: 1.5rem;
    }}
    p {{
      color: #94a3b8;
      margin: 0 0 20px 0;
      font-size: 0.95rem;
    }}
    .btn {{
      display: inline-block;
      padding: 10px 24px;
      background: #6366f1;
      color: white;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🎉</div>
    <h2>GitHub Connected!</h2>
    <p>Successfully authenticated as <strong>@{user_login}</strong> with full repository permissions.</p>
    <a href="/ui" class="btn">Continue to Dashboard</a>
  </div>
</body>
</html>"""
    )


@github_oauth_router.get("/status", summary="Get GitHub Connection Status")
async def github_status() -> dict[str, Any]:
    """Check current GitHub authentication status and permissions."""
    load_dotenv(DOTENV_PATH, override=True)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    client_id = os.environ.get("GITHUB_CLIENT_ID")

    if not token:
        return {
            "authenticated": False,
            "has_client_id": bool(client_id),
            "user": None,
        }

    # Verify token against GitHub API
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        resp = requests.get("https://api.github.com/user", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            scopes_header = resp.headers.get("x-oauth-scopes", "")
            scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
            has_repo = "repo" in scopes or "public_repo" in scopes
            return {
                "authenticated": True,
                "user": data.get("login"),
                "name": data.get("name"),
                "avatar_url": data.get("avatar_url"),
                "scopes": scopes,
                "has_repo_scope": has_repo,
                "has_client_id": bool(client_id),
            }
        else:
            return {
                "authenticated": False,
                "error": f"Token verification returned HTTP {resp.status_code}",
                "has_client_id": bool(client_id),
            }
    except Exception as exc:
        return {
            "authenticated": False,
            "error": str(exc),
            "has_client_id": bool(client_id),
        }
