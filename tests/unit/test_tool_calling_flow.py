"""Unit and integration tests for safe tool-calling flow and conversation continuation."""

import pytest
from typing import Any, Dict
from harness.llm.base import ChatMessage, LLMResponse, ToolCallDefinition
from harness.tools.base import BaseTool, ToolResult
from harness.tools.registry import ToolRegistry


class SafeEchoTool(BaseTool):
    """A safe test tool that returns uppercase text with word count."""

    name = "echo_transformer"
    description = "Transforms an input text string into uppercase and returns word count"
    parameters_schema = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Input text to transform",
            },
            "prefix": {
                "type": "string",
                "description": "Optional prefix to prepend",
            },
        },
        "required": ["text"],
    }

    async def execute(self, text: str, prefix: str = "", **kwargs: Any) -> ToolResult:
        transformed = f"{prefix}{text.upper()}"
        word_count = len(text.split())
        return ToolResult(
            success=True,
            output=f"Transformed: '{transformed}', Words: {word_count}",
            data={"transformed": transformed, "word_count": word_count},
        )


@pytest.mark.asyncio
async def test_complete_tool_calling_conversation_cycle():
    """Verify that a tool call requested by an LLM is executed, validated, and returned as a message."""
    registry = ToolRegistry()
    tool = SafeEchoTool()
    registry.register(tool)

    # 1. Verify schema generation
    schemas = registry.get_openai_schemas()
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "echo_transformer"

    # 2. Simulate model response requesting a tool call
    model_response = LLMResponse(
        content="I will transform the text using the echo tool.",
        tool_calls=[
            ToolCallDefinition(
                id="call_echo_1",
                name="echo_transformer",
                arguments={"text": "hello world from ai harness", "prefix": "OUT: "},
            )
        ],
        finish_reason="tool_calls",
        prompt_tokens=45,
        completion_tokens=25,
        total_tokens=70,
        model="gemini-2.0-flash",
    )

    # 3. Conversation history tracking
    history = [
        ChatMessage(role="system", content="You are a helpful coding harness assistant."),
        ChatMessage(role="user", content="Please uppercase 'hello world from ai harness'"),
    ]

    # Add assistant response with tool calls
    history.append(
        ChatMessage(
            role="assistant",
            content=model_response.content,
            tool_calls=[
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": str(tc.arguments)},
                }
                for tc in model_response.tool_calls
            ],
        )
    )

    # 4. Dispatch and execute tool call
    for tc in model_response.tool_calls:
        result = await registry.execute(tc.name, tc.arguments)
        assert result.success
        assert "HELLO WORLD FROM AI HARNESS" in result.output
        assert result.data["word_count"] == 5

        # 5. Append tool result message to conversation
        history.append(
            ChatMessage(
                role="tool",
                name=tc.name,
                tool_call_id=tc.id,
                content=result.to_message_content(),
            )
        )

    assert len(history) == 4
    assert history[3].role == "tool"
    assert history[3].tool_call_id == "call_echo_1"
    assert "HELLO WORLD" in history[3].content


@pytest.mark.asyncio
async def test_tool_calling_safety_and_error_handling():
    """Verify safe error propagation when tool calling encounters invalid arguments or unknown tools."""
    registry = ToolRegistry()
    registry.register(SafeEchoTool())

    # Case 1: Missing required field
    res_missing = await registry.execute("echo_transformer", {})
    assert not res_missing.success
    assert "Missing required parameter: 'text'" in res_missing.error

    # Case 2: Invalid type
    res_type = await registry.execute("echo_transformer", {"text": 12345})
    assert not res_type.success
    assert "Invalid type for parameter 'text'" in res_type.error

    # Case 3: Unknown tool
    res_unknown = await registry.execute("non_existent_tool", {"text": "hello"})
    assert not res_unknown.success
    assert "Unknown tool 'non_existent_tool'" in res_unknown.error
