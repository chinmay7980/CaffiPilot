"""Unit tests for tool registration, discovery, and argument validation."""

import pytest
from harness.tools.base import BaseTool, ToolResult
from harness.tools.registry import ToolRegistry
from harness.tools.validator import validate_tool_arguments


class SampleCalculatorTool(BaseTool):
    """Dummy tool for testing argument validation."""

    name = "calculate"
    description = "Perform basic arithmetic calculations"
    parameters_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "Operation name",
            },
            "a": {"type": "number", "description": "First operand"},
            "b": {"type": "number", "description": "Second operand"},
            "round_result": {"type": "boolean", "description": "Optional rounding flag"},
        },
        "required": ["operation", "a", "b"],
    }

    async def execute(
        self, operation: str, a: float, b: float, round_result: bool = False, **kwargs
    ) -> ToolResult:
        if operation == "add":
            res = a + b
        elif operation == "subtract":
            res = a - b
        elif operation == "multiply":
            res = a * b
        elif operation == "divide":
            if b == 0:
                return ToolResult(success=False, output="", error="Division by zero")
            res = a / b
        else:
            return ToolResult(success=False, output="", error=f"Unknown op {operation}")

        if round_result:
            res = round(res)
        return ToolResult(success=True, output=str(res), data={"result": res})


@pytest.mark.asyncio
async def test_tool_registration_and_discovery():
    """Verify tool registration, discovery, and schema generation."""
    registry = ToolRegistry()
    tool = SampleCalculatorTool()
    registry.register(tool)

    assert registry.has_tool("calculate")
    assert registry.get("calculate") == tool
    assert "calculate" in registry.get_tool_names()

    schemas = registry.get_openai_schemas()
    assert len(schemas) == 1
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "calculate"
    assert schemas[0]["function"]["parameters"]["required"] == ["operation", "a", "b"]


@pytest.mark.asyncio
async def test_successful_tool_execution():
    """Verify successful argument validation and execution."""
    registry = ToolRegistry()
    registry.register(SampleCalculatorTool())

    res = await registry.execute("calculate", {"operation": "add", "a": 10, "b": 25})
    assert res.success
    assert res.output == "35"
    assert res.data["result"] == 35


@pytest.mark.asyncio
async def test_missing_required_arguments():
    """Verify error when required arguments are omitted."""
    registry = ToolRegistry()
    registry.register(SampleCalculatorTool())

    res = await registry.execute("calculate", {"operation": "add", "a": 10})
    assert not res.success
    assert "Missing required parameter: 'b'" in res.error


@pytest.mark.asyncio
async def test_invalid_argument_types():
    """Verify error when arguments have wrong data types."""
    registry = ToolRegistry()
    registry.register(SampleCalculatorTool())

    # String passed instead of number
    res = await registry.execute(
        "calculate", {"operation": "add", "a": "ten", "b": 25}
    )
    assert not res.success
    assert "Invalid type for parameter 'a': expected number, received str" in res.error

    # Boolean passed where integer/number is expected
    res_bool = await registry.execute(
        "calculate", {"operation": "add", "a": True, "b": 25}
    )
    assert not res_bool.success
    assert "received boolean" in res_bool.error


@pytest.mark.asyncio
async def test_enum_constraint_validation():
    """Verify error when an argument violates enum choices."""
    registry = ToolRegistry()
    registry.register(SampleCalculatorTool())

    res = await registry.execute(
        "calculate", {"operation": "exponent", "a": 2, "b": 3}
    )
    assert not res.success
    assert "Must be one of ['add', 'subtract', 'multiply', 'divide']" in res.error


@pytest.mark.asyncio
async def test_unknown_tool_execution():
    """Verify safe error response when invoking an unregistered tool."""
    registry = ToolRegistry()
    registry.register(SampleCalculatorTool())

    res = await registry.execute("non_existent_tool", {"foo": "bar"})
    assert not res.success
    assert "Unknown tool 'non_existent_tool'" in res.error
    assert "'calculate'" in res.error


@pytest.mark.asyncio
async def test_malformed_json_argument_rejection():
    """Verify detection and rejection of malformed raw JSON strings."""
    registry = ToolRegistry()
    registry.register(SampleCalculatorTool())

    malformed_args = {
        "_raw_arguments_malformed": "{operation: 'add', a: 10,",
        "_error": "Expecting property name enclosed in double quotes",
    }
    res = await registry.execute("calculate", malformed_args)
    assert not res.success
    assert "Malformed JSON in tool arguments" in res.error
