"""Git tools for version control inspection, diff analysis, and safety checkpoints."""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
from harness.tools.base import BaseTool, ToolResult


async def _run_git(workspace_root: str, *args: str) -> tuple[int, str, str]:
    """Helper to run git command in the workspace."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=workspace_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (
            proc.returncode if proc.returncode is not None else -1,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
    except Exception as e:
        return -1, "", str(e)


class GitDiffTool(BaseTool):
    """Tool for viewing git diff of modifications."""

    name = "git_diff"
    description = "View git diff showing uncommitted or staged changes in the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {
            "cached": {
                "type": "boolean",
                "description": "If True, view staged diff (git diff --cached). Default is False.",
            },
            "path": {
                "type": "string",
                "description": "Optional specific file or directory path to diff.",
            },
        },
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(
        self, cached: bool = False, path: Optional[str] = None, **kwargs: Any
    ) -> ToolResult:
        cmd = ["diff"]
        if cached:
            cmd.append("--cached")
        if path:
            cmd.extend(["--", path])

        code, out, err = await _run_git(self.workspace_root, *cmd)
        if code != 0:
            return ToolResult(
                success=False,
                output="",
                error=f"git diff failed (exit {code}): {err}",
            )

        output = out.strip() if out.strip() else "[No diff - working tree clean or no changes detected]"
        return ToolResult(success=True, output=output)


class GitStatusTool(BaseTool):
    """Tool for checking working tree status."""

    name = "git_status"
    description = "Check git status to see modified, untracked, or deleted files."
    parameters_schema = {
        "type": "object",
        "properties": {},
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, **kwargs: Any) -> ToolResult:
        code, out, err = await _run_git(self.workspace_root, "status", "--short")
        if code != 0:
            return ToolResult(
                success=False,
                output="",
                error=f"git status failed: {err}",
            )
        output = out.strip() if out.strip() else "[Working tree clean]"
        return ToolResult(success=True, output=output)


class GitCheckpointTool(BaseTool):
    """Tool for creating a safety checkpoint before risky modifications."""

    name = "git_checkpoint"
    description = "Create a safety checkpoint of the current repository state to enable rollback if needed."
    parameters_schema = {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "Descriptive label for this checkpoint",
            },
        },
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, label: str = "auto_checkpoint", **kwargs: Any) -> ToolResult:
        # Check if git is initialized
        code, _, _ = await _run_git(self.workspace_root, "rev-parse", "--is-inside-work-tree")
        if code != 0:
            # Initialize git if not already a repo
            await _run_git(self.workspace_root, "init")
            await _run_git(self.workspace_root, "config", "user.name", "AI Harness")
            await _run_git(self.workspace_root, "config", "user.email", "harness@agent.local")

        # Stage and commit checkpoint
        await _run_git(self.workspace_root, "add", "-A")
        code, out, err = await _run_git(
            self.workspace_root, "commit", "-m", f"checkpoint: {label}", "--allow-empty"
        )
        if code == 0:
            return ToolResult(
                success=True,
                output=f"Successfully created checkpoint '{label}'",
                data={"label": label},
            )
        return ToolResult(
            success=False,
            output="",
            error=f"Failed to create checkpoint: {err}",
        )


class GitRollbackTool(BaseTool):
    """Tool for reverting repository modifications to the last clean checkpoint."""

    name = "git_rollback"
    description = "Rollback uncommitted changes or revert the repository back to the last checkpoint."
    parameters_schema = {
        "type": "object",
        "properties": {
            "hard": {
                "type": "boolean",
                "description": "If True, resets all tracked and untracked changes (git reset --hard & clean -fd). Default is True.",
            },
        },
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, hard: bool = True, **kwargs: Any) -> ToolResult:
        if hard:
            code1, out1, err1 = await _run_git(self.workspace_root, "reset", "--hard", "HEAD")
            code2, out2, err2 = await _run_git(self.workspace_root, "clean", "-fd")
            if code1 == 0 and code2 == 0:
                return ToolResult(
                    success=True,
                    output="Successfully rolled back all workspace changes to the last commit/checkpoint.",
                )
            return ToolResult(
                success=False,
                output="",
                error=f"Rollback failed: {err1} {err2}",
            )
        else:
            code, out, err = await _run_git(self.workspace_root, "checkout", "--", ".")
            return ToolResult(
                success=code == 0,
                output="Reverted tracked changes.",
                error=err if code != 0 else None,
            )


class GitLogTool(BaseTool):
    """Tool for showing recent commit history."""

    name = "git_log"
    description = "Show recent commit history of the repository."
    parameters_schema = {
        "type": "object",
        "properties": {
            "max_count": {
                "type": "integer",
                "description": "Max commits to show (default: 10)",
            }
        },
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, max_count: int = 10, **kwargs: Any) -> ToolResult:
        code, out, err = await _run_git(self.workspace_root, "log", f"-n{max_count}", "--oneline")
        if code != 0:
            return ToolResult(success=False, output="", error=f"git log failed: {err}")
        return ToolResult(success=True, output=out.strip() or "No commits.")


class GitCreateBranchTool(BaseTool):
    """Tool for creating a task-specific branch."""

    name = "git_create_branch"
    description = "Create and checkout a new task-specific branch."
    parameters_schema = {
        "type": "object",
        "properties": {
            "branch_name": {
                "type": "string",
                "description": "Name of the new branch",
            }
        },
        "required": ["branch_name"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, branch_name: str, **kwargs: Any) -> ToolResult:
        code, out, err = await _run_git(self.workspace_root, "checkout", "-b", branch_name)
        if code != 0:
            return ToolResult(success=False, output="", error=f"Failed to create branch: {err}")
        return ToolResult(success=True, output=out.strip() or f"Created and switched to branch '{branch_name}'")


class GitCommitTool(BaseTool):
    """Tool for committing changes to the repository."""

    name = "git_commit"
    description = "Commit changes to the repository. Only use when explicitly authorized."
    parameters_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Commit message",
            },
            "stage_all": {
                "type": "boolean",
                "description": "Whether to stage all tracked and untracked changes first (git add -A). Default is True.",
            }
        },
        "required": ["message"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, message: str, stage_all: bool = True, **kwargs: Any) -> ToolResult:
        if stage_all:
            await _run_git(self.workspace_root, "add", "-A")
        code, out, err = await _run_git(self.workspace_root, "commit", "-m", message)
        if code != 0:
            return ToolResult(success=False, output="", error=f"git commit failed: {err}")
        return ToolResult(success=True, output=out.strip() or f"Committed with message: '{message}'")
