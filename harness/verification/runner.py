"""Automated test execution and result parsing engine."""

import asyncio
import os
import re
import signal
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from harness.verification.detector import detect_test_command


class VerificationResult(BaseModel):
    """Structured outcome of a verification / test run."""

    passed: bool = Field(description="True if all tests passed without failure")
    exit_code: int = Field(default=0, description="Process exit code")
    total_tests: int = Field(default=0, description="Total tests discovered")
    passed_tests: int = Field(default=0, description="Number of passed tests")
    failed_tests: int = Field(default=0, description="Number of failed tests")
    skipped_tests: int = Field(default=0, description="Number of skipped tests")
    summary: str = Field(default="", description="High-level test run summary")
    raw_output: str = Field(default="", description="Raw stdout/stderr test output")
    command_used: str = Field(default="", description="Test command that was executed")


def parse_pytest_output(output: str, exit_code: int) -> tuple[int, int, int, int]:
    """Extracts passed, failed, and skipped counts from pytest output."""
    passed = 0
    failed = 0
    skipped = 0

    m_passed = re.search(r"(\d+)\s+passed", output)
    m_failed = re.search(r"(\d+)\s+failed", output)
    m_skipped = re.search(r"(\d+)\s+skipped", output)
    m_errors = re.search(r"(\d+)\s+error", output)

    if m_passed:
        passed = int(m_passed.group(1))
    if m_failed:
        failed = int(m_failed.group(1))
    if m_errors:
        failed += int(m_errors.group(1))
    if m_skipped:
        skipped = int(m_skipped.group(1))

    total = passed + failed + skipped
    # If exit code indicates failure but no failure count parsed, mark at least 1 failed
    if exit_code != 0 and failed == 0 and total == 0:
        total = 1
        failed = 1
    elif total == 0 and exit_code == 0:
        total = 1
        passed = 1

    return total, passed, failed, skipped


class VerificationRunner:
    """Runs tests and analyzes results for repository verification."""

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def run(
        self, custom_command: Optional[str] = None, timeout: int = 90
    ) -> VerificationResult:
        cmd = custom_command or detect_test_command(self.workspace_root)
        if not cmd:
            return VerificationResult(
                passed=True,
                exit_code=0,
                summary="No test runner detected in repository. Marked as unverified/passed by default.",
                raw_output="[No automated tests found in workspace]",
                command_used="none",
            )

        env = os.environ.copy()
        venv_bin = os.path.dirname(sys.executable)
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=self.workspace_root,
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
                try:
                    if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                except Exception:
                    pass
                return VerificationResult(
                    passed=False,
                    exit_code=-1,
                    summary=f"Test run timed out after {timeout} seconds.",
                    raw_output=f"[Test execution exceeded timeout of {timeout}s]",
                    command_used=cmd,
                )

            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode if process.returncode is not None else -1
            combined = stdout_str + ("\n" + stderr_str if stderr_str else "")

            total, passed_cnt, failed_cnt, skipped_cnt = parse_pytest_output(
                combined, exit_code
            )
            is_passed = (exit_code == 0 and failed_cnt == 0)

            summary = (
                f"Tests: {passed_cnt} passed, {failed_cnt} failed, {skipped_cnt} skipped "
                f"(Exit code {exit_code})"
            )

            return VerificationResult(
                passed=is_passed,
                exit_code=exit_code,
                total_tests=total,
                passed_tests=passed_cnt,
                failed_tests=failed_cnt,
                skipped_tests=skipped_cnt,
                summary=summary,
                raw_output=combined,
                command_used=cmd,
            )

        except Exception as e:
            return VerificationResult(
                passed=False,
                exit_code=-1,
                summary=f"Failed to execute verification tests: {str(e)}",
                raw_output=str(e),
                command_used=cmd,
            )
