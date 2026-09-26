"""File operations tools with strict workspace sandboxing."""

import os
import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from harness.tools.base import BaseTool, ToolResult


def resolve_safe_path(workspace_root: str, target_path: str) -> Path:
    """Resolves and validates that the target path is strictly contained within workspace_root."""
    root = Path(workspace_root).resolve()
    # Normalize path
    target = (root / target_path).resolve()
    
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Security Error: Access denied. Path '{target_path}' escapes workspace root '{root}'."
        )
    return target


class ReadFileTool(BaseTool):
    """Tool for reading file contents with line range and pagination support."""

    name = "read_file"
    description = "Read file contents from the workspace. Supports reading full files or specific line slices."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative or absolute path to the file within workspace",
            },
            "start_line": {
                "type": "integer",
                "description": "Starting line number (1-indexed, inclusive). Optional.",
            },
            "end_line": {
                "type": "integer",
                "description": "Ending line number (1-indexed, inclusive). Optional.",
            },
        },
        "required": ["path"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            target = resolve_safe_path(self.workspace_root, path)
            if not target.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: '{path}'",
                )
            if target.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path '{path}' is a directory, not a file. Use 'list_directory' instead.",
                )

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_line = max(1, start_line) if start_line is not None else 1
            e_line = min(total_lines, end_line) if end_line is not None else total_lines

            if s_line > total_lines:
                return ToolResult(
                    success=True,
                    output=f"[File '{path}' has {total_lines} lines. start_line {s_line} is out of bounds]",
                    data={"total_lines": total_lines, "lines_read": 0},
                )

            selected_lines = lines[s_line - 1 : e_line]
            formatted_lines = [
                f"{i + s_line:4d} | {line.rstrip()}"
                for i, line in enumerate(selected_lines)
            ]
            output = "\n".join(formatted_lines)
            return ToolResult(
                success=True,
                output=output,
                data={"total_lines": total_lines, "start_line": s_line, "end_line": e_line},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class WriteFileTool(BaseTool):
    """Tool for creating or completely overwriting a file."""

    name = "write_file"
    description = "Create a new file or overwrite an existing file with complete content."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to create or overwrite",
            },
            "content": {
                "type": "string",
                "description": "Full text content to write into the file",
            },
        },
        "required": ["path", "content"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, path: str, content: str, **kwargs: Any) -> ToolResult:
        try:
            target = resolve_safe_path(self.workspace_root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            bytes_written = len(content.encode("utf-8"))
            return ToolResult(
                success=True,
                output=f"Successfully wrote {bytes_written} bytes to '{path}'",
                data={"path": path, "bytes": bytes_written},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class EditFileTool(BaseTool):
    """Tool for surgical search-and-replace edits inside existing files."""

    name = "edit_file"
    description = "Make precise search-and-replace modifications to an existing file."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "target_content": {
                "type": "string",
                "description": "Exact text block to find and replace",
            },
            "replacement_content": {
                "type": "string",
                "description": "New text block to insert in place of target_content",
            },
            "allow_multiple": {
                "type": "boolean",
                "description": "If True, replaces all occurrences. Default is False (errors if multiple matches found).",
            },
        },
        "required": ["path", "target_content", "replacement_content"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(
        self,
        path: str,
        target_content: str,
        replacement_content: str,
        allow_multiple: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            target = resolve_safe_path(self.workspace_root, path)
            if not target.exists():
                return ToolResult(
                    success=False, output="", error=f"File not found: '{path}'"
                )

            with open(target, "r", encoding="utf-8") as f:
                content = f.read()

            count = content.count(target_content)
            if count == 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Target content not found in '{path}'. Make sure target_content matches exact characters and indentation.",
                )

            if count > 1 and not allow_multiple:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Target content matched {count} times in '{path}'. Set allow_multiple=True or provide more surrounding context to make the match unique.",
                )

            if allow_multiple:
                new_content = content.replace(target_content, replacement_content)
            else:
                new_content = content.replace(target_content, replacement_content, 1)

            with open(target, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                success=True,
                output=f"Successfully replaced {count if allow_multiple else 1} occurrence(s) in '{path}'",
                data={"path": path, "replacements": count if allow_multiple else 1},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ListDirectoryTool(BaseTool):
    """Tool for exploring directory structures and file trees."""

    name = "list_files"
    description = "List files and subdirectories in the workspace with hierarchy and file sizes."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to directory within workspace. Defaults to '.' (root)",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum directory traversal depth (default: 2, max: 5)",
            },
        },
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(
        self, path: str = ".", max_depth: int = 2, **kwargs: Any
    ) -> ToolResult:
        try:
            target = resolve_safe_path(self.workspace_root, path)
            if not target.exists():
                return ToolResult(
                    success=False, output="", error=f"Directory not found: '{path}'"
                )
            if not target.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path '{path}' is a file, not a directory.",
                )

            max_d = min(max(1, max_depth), 5)
            lines: List[str] = []
            
            def _traverse(current: Path, depth: int, prefix: str = ""):
                if depth > max_d:
                    return
                try:
                    entries = sorted(
                        list(current.iterdir()),
                        key=lambda e: (not e.is_dir(), e.name.lower()),
                    )
                except PermissionError:
                    lines.append(f"{prefix}[Permission Denied]")
                    return

                for entry in entries:
                    if entry.name.startswith(".") or entry.name in {
                        "__pycache__",
                        "node_modules",
                        ".git",
                        ".venv",
                        "venv",
                        "build",
                        "dist",
                    }:
                        continue
                    if entry.is_dir():
                        lines.append(f"{prefix}📁 {entry.name}/")
                        _traverse(entry, depth + 1, prefix + "  ")
                    else:
                        size = entry.stat().st_size
                        size_str = f"{size} B" if size < 1024 else f"{size / 1024:.1f} KB"
                        lines.append(f"{prefix}📄 {entry.name} ({size_str})")

            _traverse(target, 1)
            output = "\n".join(lines) if lines else "[Directory is empty]"
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class GetFileMetadataTool(BaseTool):
    """Tool for retrieving file metadata."""

    name = "get_file_metadata"
    description = "Return file size, extension, and other safe metadata for a specific file."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to inspect",
            }
        },
        "required": ["path"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, path: str, **kwargs: Any) -> ToolResult:
        try:
            target = resolve_safe_path(self.workspace_root, path)
            if not target.exists():
                return ToolResult(success=False, output="", error=f"File not found: '{path}'")
            if target.is_dir():
                return ToolResult(success=False, output="", error=f"Path '{path}' is a directory, not a file.")

            stat = target.stat()
            size = stat.st_size
            size_str = f"{size} B" if size < 1024 else f"{size / 1024:.1f} KB"
            ext = target.suffix or "[No Extension]"
            
            output = (
                f"Metadata for '{path}':\n"
                f"- Size: {size_str}\n"
                f"- Extension: {ext}\n"
                f"- Read Only: {'Yes' if not os.access(target, os.W_OK) else 'No'}\n"
            )
            return ToolResult(
                success=True, 
                output=output, 
                data={"size": size, "extension": target.suffix}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class InspectProjectTool(BaseTool):
    """Tool for identifying project structure, languages, dependency manifests, and config files."""

    name = "inspect_project"
    description = "Identify project structure, languages, dependency manifests, and important configuration files in the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {},
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            root = Path(self.workspace_root).resolve()
            
            manifests = []
            configs = []
            languages = set()
            directories = set()

            IMPORTANT_MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt", "pom.xml", "build.gradle", "Cargo.toml", "go.mod"}
            IMPORTANT_CONFIGS = {"Makefile", "docker-compose.yml", "Dockerfile", ".env.example", "tsconfig.json", "webpack.config.js"}
            LANG_EXTS = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java", ".rs": "Rust", ".go": "Go", ".cpp": "C++", ".c": "C", ".rb": "Ruby", ".php": "PHP", ".html": "HTML", ".css": "CSS"}
            
            for current_dir, dirs, files in os.walk(root):
                # Prune ignored directories
                dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"} and not d.startswith(".")]
                
                rel_dir = Path(current_dir).relative_to(root)
                if str(rel_dir) != ".":
                    directories.add(str(rel_dir).split(os.sep)[0])
                
                for file in files:
                    if file in IMPORTANT_MANIFESTS:
                        manifests.append(str((Path(current_dir) / file).relative_to(root)))
                    elif file in IMPORTANT_CONFIGS:
                        configs.append(str((Path(current_dir) / file).relative_to(root)))
                        
                    ext = Path(file).suffix
                    if ext in LANG_EXTS:
                        languages.add(LANG_EXTS[ext])
                        
            output = "Project Inspection Report:\n\n"
            output += "Primary Languages Detected:\n" + ("- " + "\n- ".join(sorted(languages)) if languages else "- [None]") + "\n\n"
            output += "Dependency Manifests:\n" + ("- " + "\n- ".join(sorted(manifests)) if manifests else "- [None]") + "\n\n"
            output += "Important Configs:\n" + ("- " + "\n- ".join(sorted(configs)) if configs else "- [None]") + "\n\n"
            output += "Key Root Directories:\n" + ("- " + "\n- ".join(sorted(directories)) if directories else "- [Empty]")
            
            return ToolResult(
                success=True, 
                output=output, 
                data={
                    "languages": list(languages),
                    "manifests": manifests,
                    "configs": configs,
                    "directories": list(directories)
                }
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class DeleteFileTool(BaseTool):
    """Tool for safely deleting a file within the workspace."""

    name = "delete_file"
    description = "Delete a file only within the active workspace."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to delete",
            }
        },
        "required": ["path"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, path: str, **kwargs: Any) -> ToolResult:
        try:
            target = resolve_safe_path(self.workspace_root, path)
            if not target.exists():
                return ToolResult(success=False, output="", error=f"File not found: '{path}'")
            if target.is_dir():
                return ToolResult(success=False, output="", error=f"Path '{path}' is a directory, not a file.")

            target.unlink()
            return ToolResult(success=True, output=f"Successfully deleted '{path}'")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ApplyPatchTool(BaseTool):
    """Tool for applying a structured unified diff patch."""

    name = "apply_patch"
    description = "Apply a structured unified diff patch to files in the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {
            "patch_content": {
                "type": "string",
                "description": "The full unified diff patch content to apply",
            }
        },
        "required": ["patch_content"],
    }

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root

    async def execute(self, patch_content: str, **kwargs: Any) -> ToolResult:
        try:
            if "../" in patch_content:
                return ToolResult(
                    success=False, 
                    output="", 
                    error="Security Error: Patch contains path traversal ('../') which is prohibited."
                )

            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
                f.write(patch_content)
                temp_path = f.name

            proc = await asyncio.create_subprocess_exec(
                "patch", "-p0", "-i", temp_path,
                cwd=self.workspace_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            os.unlink(temp_path)

            if proc.returncode == 0:
                return ToolResult(success=True, output="Patch applied successfully.")
            else:
                err = stderr.decode("utf-8", errors="replace").strip()
                if not err:
                    err = stdout.decode("utf-8", errors="replace").strip()
                return ToolResult(success=False, output="", error=f"Failed to apply patch: {err}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
