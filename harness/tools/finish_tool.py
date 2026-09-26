"""Tool for terminating and summarizing the autonomous task execution."""

from typing import Any, Dict
from harness.tools.base import BaseTool, ToolResult


class FinishTaskTool(BaseTool):
    """Tool invoked by the agent when the coding task is completed and verified."""

    name = "finish_task"
    description = (
        "Signal completion of the coding task. "
        "Provide a comprehensive final summary of the issue, files modified, test verification results, and solution outcome."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Markdown summary of the solution, changes made, and verification status.",
            },
            "verification_status": {
                "type": "string",
                "enum": ["passed", "failed", "unverified"],
                "description": "Overall status of test suite verification",
            },
            "files_modified": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of relative file paths modified during the task",
            },
        },
        "required": ["summary", "verification_status"],
    }

    async def execute(
        self,
        summary: str,
        verification_status: str = "passed",
        files_modified: Any = None,
        **kwargs: Any,
    ) -> ToolResult:
        files = files_modified if isinstance(files_modified, list) else []
        return ToolResult(
            success=True,
            output=f"Task completed successfully. Verification: {verification_status}.\n\nSummary:\n{summary}",
            data={
                "completed": True,
                "summary": summary,
                "verification_status": verification_status,
                "files_modified": files,
            },
        )
