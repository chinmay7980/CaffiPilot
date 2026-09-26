"""Tool registry for registering, discovering, validating, and dispatching tool executions."""

import logging
from typing import Any, Dict, List, Optional
from harness.tools.base import BaseTool, ToolResult
from harness.tools.file_tools import (
    EditFileTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
    GetFileMetadataTool,
    InspectProjectTool,
    ApplyPatchTool,
    DeleteFileTool,
)
from harness.tools.finish_tool import FinishTaskTool
from harness.tools.git_tools import (
    GitCheckpointTool,
    GitDiffTool,
    GitRollbackTool,
    GitStatusTool,
    GitLogTool,
    GitCreateBranchTool,
    GitCommitTool,
)
from harness.tools.search_tools import FindFilesTool, GrepSearchTool
from harness.tools.terminal_tools import RunCommandTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry maintaining available tools and dispatching safe, validated tool executions."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance into the registry."""
        if not hasattr(tool, "name") or not tool.name:
            raise ValueError("Cannot register a tool without a valid 'name' attribute.")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool '{tool.name}'")

    def unregister(self, name: str) -> Optional[BaseTool]:
        """Removes a tool from the registry."""
        return self._tools.pop(name, None)

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieves a tool instance by name."""
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Checks if a tool is registered."""
        return name in self._tools

    def list_tools(self) -> List[BaseTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """Returns a list of all registered tool names."""
        return list(self._tools.keys())

    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        """Returns OpenAI-compatible function schemas for all registered tools."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Validates arguments and dispatches execution to the registered tool safely."""
        tool = self.get(name)
        if not tool:
            available = ", ".join([f"'{t}'" for t in self.get_tool_names()])
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool '{name}'. Available tools are: {available or 'None'}.",
            )

        if not isinstance(arguments, dict):
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid arguments payload for tool '{name}': expected dictionary, received {type(arguments).__name__}.",
            )

        # 1. Validate arguments against schema
        is_valid, validation_error = tool.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid arguments for tool '{name}': {validation_error}",
                data={"validation_error": validation_error},
            )

        # 2. Filter internal keys starting with '_' before calling execute
        clean_args = {k: v for k, v in arguments.items() if not k.startswith("_")}

        # 3. Execute tool safely
        try:
            return await tool.execute(**clean_args)
        except TypeError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Signature error invoking tool '{name}': {str(e)}",
            )
        except Exception as e:
            logger.exception(f"Unhandled exception during tool '{name}' execution")
            return ToolResult(
                success=False,
                output="",
                error=f"Execution error in tool '{name}': {str(e)}",
            )


def create_default_registry(workspace_root: str) -> ToolRegistry:
    """Creates a standard tool registry populated with all core tools bound to the given workspace."""
    registry = ToolRegistry()
    registry.register(ReadFileTool(workspace_root))
    registry.register(WriteFileTool(workspace_root))
    registry.register(EditFileTool(workspace_root))
    registry.register(ListDirectoryTool(workspace_root))
    registry.register(GetFileMetadataTool(workspace_root))
    registry.register(InspectProjectTool(workspace_root))
    registry.register(ApplyPatchTool(workspace_root))
    registry.register(DeleteFileTool(workspace_root))
    registry.register(GrepSearchTool(workspace_root))
    registry.register(FindFilesTool(workspace_root))
    registry.register(RunCommandTool(workspace_root))
    registry.register(GitDiffTool(workspace_root))
    registry.register(GitStatusTool(workspace_root))
    registry.register(GitCheckpointTool(workspace_root))
    registry.register(GitRollbackTool(workspace_root))
    registry.register(GitLogTool(workspace_root))
    registry.register(GitCreateBranchTool(workspace_root))
    registry.register(GitCommitTool(workspace_root))
    registry.register(FinishTaskTool())
    return registry
