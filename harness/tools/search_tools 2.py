"""Search tools for code discovery, regex grep, and file pattern matching."""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from harness.tools.base import BaseTool, ToolResult
from harness.tools.file_tools import resolve_safe_path

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "build",
    "dist",
    ".idea",
    ".vscode",
    ".harness_checkpoints",
}


class GrepSearchTool(BaseTool):
    """Tool for searching code across files using regex or literal text patterns."""

    name = "search_code"
    description = "Search for a regex or text pattern within workspace files. Returns matching lines with line numbers."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Regex or text pattern to search for",
            },
            "file_pattern": {
                "type": "string",
                "description": "Optional glob filter for filenames (e.g., '*.py', '*.ts')",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether to perform case-sensitive search. Default is True.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum matching lines to return (default: 50, max: 100)",
            },
        },
        "required": ["query"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(
        self,
        query: str,
        file_pattern: Optional[str] = None,
        case_sensitive: bool = True,
        max_results: int = 50,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            root = Path(self.workspace_root).resolve()
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(query, flags)
            except re.error as e:
                return ToolResult(
                    success=False, output="", error=f"Invalid regex pattern '{query}': {e}"
                )

            max_matches = min(max(1, max_results), 100)
            matches: List[str] = []
            files_searched = 0

            for current_dir, dirs, files in os.walk(root):
                # Prune ignored directories
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

                for file in files:
                    if file_pattern and not fnmatch.fnmatch(file, file_pattern):
                        continue

                    file_path = Path(current_dir) / file
                    try:
                        rel_path = file_path.relative_to(root)
                    except ValueError:
                        continue

                    files_searched += 1
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                if regex.search(line):
                                    matches.append(
                                        f"{rel_path}:{line_num}: {line.strip()}"
                                    )
                                    if len(matches) >= max_matches:
                                        break
                    except Exception:
                        continue

                    if len(matches) >= max_matches:
                        break
                if len(matches) >= max_matches:
                    break

            if not matches:
                output = f"No matches found for pattern '{query}' across {files_searched} files."
            else:
                output = f"Found {len(matches)} match(es):\n" + "\n".join(matches)

            return ToolResult(
                success=True,
                output=output,
                data={
                    "query": query,
                    "matches_count": len(matches),
                    "files_searched": files_searched,
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FindFilesTool(BaseTool):
    """Tool for locating files by name or glob pattern."""

    name = "search_files"
    description = "Find files in the workspace matching a glob pattern (e.g. '*test*.py', 'config.json')."
    parameters_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match file names (e.g. '*.py', '*service*', '*.toml')",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of file paths to return (default: 50, max: 100)",
            },
        },
        "required": ["pattern"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(
        self, pattern: str, max_results: int = 50, **kwargs: Any
    ) -> ToolResult:
        try:
            root = Path(self.workspace_root).resolve()
            max_r = min(max(1, max_results), 100)
            matched_files: List[str] = []

            for current_dir, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

                for file in files:
                    if fnmatch.fnmatch(file, pattern):
                        full_path = Path(current_dir) / file
                        rel_path = full_path.relative_to(root)
                        matched_files.append(str(rel_path))
                        if len(matched_files) >= max_r:
                            break
                if len(matched_files) >= max_r:
                    break

            if not matched_files:
                output = f"No files found matching pattern '{pattern}'"
            else:
                output = f"Found {len(matched_files)} file(s):\n" + "\n".join(
                    matched_files
                )

            return ToolResult(
                success=True,
                output=output,
                data={"pattern": pattern, "count": len(matched_files)},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
