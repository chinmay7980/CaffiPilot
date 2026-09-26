"""Terminal command execution tool with strict sandbox security controls, command validation, environment sanitization, and output limits."""

import asyncio
import os
import re
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from harness.config import settings
from harness.tools.base import BaseTool, ToolResult
from harness.tools.file_tools import resolve_safe_path

# Approved development executables allowlist
ALLOWED_COMMANDS: Set[str] = {
    "pytest",
    "python",
    "python3",
    "npm",
    "node",
    "npx",
    "make",
    "cargo",
    "go",
    "git",
    "ruff",
    "flake8",
    "mypy",
    "eslint",
    "black",
    "pip",
    "pip3",
    "poetry",
    "pipenv",
    "yarn",
    "pnpm",
    "ls",
    "cat",
    "grep",
    "find",
    "diff",
    "echo",
    "pwd",
    "touch",
    "mkdir",
    "cp",
    "mv",
    "rm",
    "unittest",
    "tsc",
    "prettier",
}

# Blocked dangerous patterns and system commands
BLOCKED_PATTERNS: List[Tuple[str, str]] = [
    (r"\bsudo\b", "Command 'sudo' is prohibited."),
    (r"\bsu\b", "Command 'su' is prohibited."),
    (r"\bchmod\b", "Permission modification commands are prohibited."),
    (r"\bchown\b", "Ownership modification commands are prohibited."),
    (r"\bcurl\s+.*\|", "Piping remote network downloads to shell is prohibited."),
    (r"\bwget\s+.*\|", "Piping remote network downloads to shell is prohibited."),
    (r"\bnc\b|\bncat\b|\bnetcat\b", "Reverse shell / raw network sockets commands are prohibited."),
    (r"\brm\s+-rf\s+/", "System destructive commands are prohibited."),
    (r"\bshutdown\b|\breboot\b", "System control commands are prohibited."),
    (r":\(\)\{\s*:\|:&\s*\};:", "Fork bomb patterns are prohibited."),
]

# Environment keys to sanitize/strip for secret security
SECRET_ENV_KEYS: Set[str] = {
    "AI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "AZURE_OPENAI_API_KEY",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "SLACK_BOT_TOKEN",
    "DATABASE_URL",
}


import shlex

def validate_command_safety(command: str) -> Tuple[bool, Optional[str]]:
    """Validates command against safety rules, allowlist, and dangerous patterns."""
    cmd_trimmed = command.strip()
    if not cmd_trimmed:
        return False, "Empty command line provided."

    # 1. Check blocked patterns
    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_trimmed, re.IGNORECASE):
            return False, f"Security Violation: {reason}"

    # 2. Parse command tokens safely using shlex
    try:
        tokens = shlex.split(cmd_trimmed)
    except ValueError:
        tokens = cmd_trimmed.split()

    if not tokens:
        return False, "Empty command line provided."

    sub_cmds: List[List[str]] = []
    current_sub: List[str] = []
    for token in tokens:
        if token in ("&&", "||", ";", "|"):
            if current_sub:
                sub_cmds.append(current_sub)
                current_sub = []
        else:
            current_sub.append(token)
    if current_sub:
        sub_cmds.append(current_sub)

    for sub_tokens in sub_cmds:
        if not sub_tokens:
            continue
        
        idx = 0
        while idx < len(sub_tokens) and "=" in sub_tokens[idx] and not sub_tokens[idx].startswith("-"):
            idx += 1
            
        if idx >= len(sub_tokens):
            continue

        base_exec = os.path.basename(sub_tokens[idx])
        if base_exec not in ALLOWED_COMMANDS:
            return False, (
                f"Security Error: Executable '{base_exec}' is not in the approved command allowlist. "
                f"Approved executables are: {', '.join(sorted(ALLOWED_COMMANDS))}."
            )

    return True, None


def prepare_sanitized_environment() -> Dict[str, str]:
    """Creates a clean subprocess environment with secrets stripped."""
    env = os.environ.copy()
    for key in SECRET_ENV_KEYS:
        env.pop(key, None)
    
    # Prepend virtualenv bin path if available
    venv_bin = os.path.dirname(sys.executable)
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    return env


class RunCommandTool(BaseTool):
    """Tool for executing safe shell commands within the sandboxed workspace environment."""

    name = "run_command"
    description = (
        "Execute an approved development command in the workspace directory. "
        "Useful for running tests (pytest, npm test), linters, build tools, or git commands."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command line to execute (e.g., 'pytest tests/', 'git status', 'make test')",
            },
            "cwd": {
                "type": "string",
                "description": "Optional relative subdirectory within the workspace to execute the command in.",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Timeout in seconds before terminating process (default: 60, max: 300)",
            },
        },
        "required": ["command"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        **kwargs: Any,
    ) -> ToolResult:
        # 1. Command safety validation
        is_safe, error_msg = validate_command_safety(command)
        if not is_safe:
            return ToolResult(
                success=False,
                output="",
                error=error_msg,
                data={"command": command, "rejected": True, "reason": error_msg},
            )

        # 2. Workspace path resolution
        try:
            target_cwd = resolve_safe_path(self.workspace_root, cwd or ".")
        except ValueError as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                data={"command": command, "rejected": True, "reason": str(e)},
            )

        timeout = min(
            max(1, timeout_seconds or settings.harness_command_timeout),
            300,
        )
        max_output_chars = 12000

        # 3. Environment sanitization
        env = prepare_sanitized_environment()

        start_time = time.time()
        try:
            # 4. Process execution in sandbox directory
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(target_cwd),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                # Terminate process group if timeout occurs
                try:
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                except Exception:
                    pass
                
                duration = round(time.time() - start_time, 3)
                return ToolResult(
                    success=False,
                    output=f"[Command timed out after {timeout} seconds]",
                    error=f"Command '{command}' exceeded timeout of {timeout}s",
                    data={
                        "command": command,
                        "timed_out": True,
                        "timeout_seconds": timeout,
                        "duration_seconds": duration,
                    },
                )

            duration = round(time.time() - start_time, 3)
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode if process.returncode is not None else -1

            # Combined output format
            combined_parts = []
            if stdout_str:
                combined_parts.append(stdout_str)
            if stderr_str:
                combined_parts.append(f"[stderr]\n{stderr_str}")

            combined_output = "\n".join(combined_parts) if combined_parts else "[No output]"

            # Output truncation
            is_truncated = len(combined_output) > max_output_chars
            if is_truncated:
                truncated_output = (
                    combined_output[: max_output_chars // 2]
                    + f"\n\n... [Output truncated ({len(combined_output)} chars total)] ...\n\n"
                    + combined_output[-max_output_chars // 2 :]
                )
            else:
                truncated_output = combined_output

            formatted_result = (
                f"Exit Code: {exit_code}\n"
                f"{truncated_output.strip()}"
            )

            success = (exit_code == 0)
            return ToolResult(
                success=success,
                output=formatted_result,
                error=None if success else f"Command exited with non-zero code {exit_code}",
                data={
                    "command": command,
                    "exit_code": exit_code,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "duration_seconds": duration,
                    "timed_out": False,
                    "truncated": is_truncated,
                },
            )

        except Exception as e:
            duration = round(time.time() - start_time, 3)
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute command '{command}': {str(e)}",
                data={"command": command, "error": str(e), "duration_seconds": duration},
            )
