"""Error classification, recovery advice, and bounded retry management."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorRecoveryManager:
    """Detects failure patterns, tracks error repetitions, and suggests targeted recovery actions."""

    def __init__(self, max_consecutive_failures: int = 4):
        self.max_consecutive_failures = max_consecutive_failures
        self.consecutive_failures: int = 0
        self.error_counts: Dict[str, int] = {}

    def record_success(self) -> None:
        """Resets consecutive failure counter on successful action."""
        self.consecutive_failures = 0

    def record_failure(self, error_msg: str) -> None:
        """Records a failure and increments counters."""
        self.consecutive_failures += 1
        key = error_msg[:60]
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

    @property
    def is_stuck(self) -> bool:
        """Returns True if the agent is stuck in an error loop exceeding the retry threshold."""
        return self.consecutive_failures >= self.max_consecutive_failures

    def format_recovery_hint(self, tool_name: str, error_msg: str) -> str:
        """Generates specific recovery instructions for the agent based on error characteristics."""
        self.record_failure(error_msg)
        error_lower = error_msg.lower()

        hint = ""
        if "target content not found" in error_lower:
            hint = (
                "Recovery Hint: The search string in `edit_file` didn't match. "
                "Use `read_file` first to view the exact lines and formatting before editing."
            )
        elif "matched multiple times" in error_lower or "matched" in error_lower and "times" in error_lower:
            hint = (
                "Recovery Hint: The target content is not unique in the file. "
                "Include more surrounding lines in `target_content` to create a unique match."
            )
        elif "file not found" in error_lower or "no such file" in error_lower:
            hint = (
                "Recovery Hint: File does not exist. Use `find_files` or `list_directory` "
                "to verify the exact relative path."
            )
        elif "timed out" in error_lower:
            hint = (
                "Recovery Hint: The terminal command took too long. "
                "If running a test suite, run only the specific test file or test case."
            )
        elif "syntaxerror" in error_lower or "indentationerror" in error_lower:
            hint = (
                "Recovery Hint: A syntax or indentation error was introduced. "
                "Read the file with `read_file` and fix the syntax immediately."
            )
        else:
            hint = (
                f"Recovery Hint: Action failed ({self.consecutive_failures} failure(s) in a row). "
                "Analyze the error carefully, adjust parameters, or inspect the file with `read_file`."
            )

        if self.is_stuck:
            hint += " [WARNING: Multiple consecutive failures detected. Consider rolling back with `git_rollback` or taking a different approach.]"

        return hint
