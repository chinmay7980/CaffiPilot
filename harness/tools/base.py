"""Base tool definitions and standardized result models."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from harness.tools.validator import validate_tool_arguments


class ToolResult(BaseModel):
    """Standardized result returned by any tool execution."""

    success: bool = Field(description="True if tool executed without fatal errors")
    output: str = Field(default="", description="Textual output of tool execution")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional structured metadata"
    )

    def to_message_content(self) -> str:
        """Formats the result as clean string content for the LLM context."""
        if self.success:
            return self.output if self.output else "Tool executed successfully (empty output)."
        return f"Error executing tool: {self.error or self.output}"


class BaseTool(ABC):
    """Abstract interface for all workspace and agent tools."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]

    def validate_arguments(self, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates incoming arguments against the tool's parameter schema."""
        return validate_tool_arguments(self.parameters_schema, arguments)

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executes the tool with keyword arguments and returns a ToolResult."""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """Converts tool definition to OpenAI tool / function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }
