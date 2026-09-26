"""Unit tests for the LLMAdapter provider abstraction, error handling, and tool calling."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from openai import APIStatusError, RateLimitError as OpenAIRateLimitError

from harness.llm.adapter import LLMAdapter
from harness.llm.base import (
    APIError,
    AuthenticationError,
    ChatMessage,
    InvalidResponseError,
    LLMTimeoutError,
    RateLimitError,
)


@pytest.mark.asyncio
async def test_missing_api_key_raises_clear_authentication_error():
    """Verify missing AI_API_KEY produces a clear, descriptive AuthenticationError."""
    adapter = LLMAdapter(api_key="", model="gpt-4o")
    with pytest.raises(AuthenticationError) as exc_info:
        await adapter.generate(
            messages=[ChatMessage(role="user", content="Hello")]
        )
    assert "Missing or invalid AI_API_KEY" in str(exc_info.value)
    assert exc_info.value.model == "gpt-4o"


@pytest.mark.asyncio
async def test_model_name_preserved_without_silent_switch():
    """Verify configured model name is strictly preserved."""
    adapter = LLMAdapter(api_key="sk-test-key", model="claude-3-5-sonnet-20241022")
    assert adapter.model == "claude-3-5-sonnet-20241022"


@pytest.mark.asyncio
async def test_successful_text_generation():
    """Verify parsing normal textual response."""
    adapter = LLMAdapter(api_key="sk-test-key", model="gpt-4o")

    mock_choice = MagicMock()
    mock_choice.message.content = "Here is the solution to your bug."
    mock_choice.message.tool_calls = None
    mock_choice.finish_reason = "stop"

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 40
    mock_response.usage.completion_tokens = 15
    mock_response.usage.total_tokens = 55
    mock_response.model = "gpt-4o"

    adapter._client = MagicMock()
    adapter._client.chat = MagicMock()
    adapter._client.chat.completions = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

    res = await adapter.generate(
        messages=[ChatMessage(role="user", content="Fix the bug")]
    )
    assert res.content == "Here is the solution to your bug."
    assert len(res.tool_calls) == 0
    assert res.prompt_tokens == 40
    assert res.completion_tokens == 15
    assert res.total_tokens == 55


@pytest.mark.asyncio
async def test_tool_call_response_parsing():
    """Verify parsing assistant response containing tool call requests."""
    adapter = LLMAdapter(api_key="sk-test-key", model="gpt-4o")

    mock_tc = MagicMock()
    mock_tc.id = "call_abc123"
    mock_tc.function.name = "read_file"
    mock_tc.function.arguments = '{"path": "calculator.py", "start_line": 1, "end_line": 10}'

    mock_choice = MagicMock()
    mock_choice.message.content = "I will inspect calculator.py"
    mock_choice.message.tool_calls = [mock_tc]
    mock_choice.finish_reason = "tool_calls"

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 60
    mock_response.usage.completion_tokens = 25
    mock_response.usage.total_tokens = 85
    mock_response.model = "gpt-4o"

    adapter._client = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

    res = await adapter.generate(
        messages=[ChatMessage(role="user", content="Read the file")]
    )
    assert len(res.tool_calls) == 1
    tc = res.tool_calls[0]
    assert tc.id == "call_abc123"
    assert tc.name == "read_file"
    assert tc.arguments["path"] == "calculator.py"
    assert tc.arguments["start_line"] == 1


@pytest.mark.asyncio
async def test_malformed_json_tool_arguments():
    """Verify handling when the model generates invalid JSON in tool call arguments."""
    adapter = LLMAdapter(api_key="sk-test-key", model="gpt-4o")

    mock_tc = MagicMock()
    mock_tc.id = "call_bad_json"
    mock_tc.function.name = "edit_file"
    mock_tc.function.arguments = '{"path": "broken.py", unquoted_key: 123}'  # Invalid JSON

    mock_choice = MagicMock()
    mock_choice.message.content = "Calling tool"
    mock_choice.message.tool_calls = [mock_tc]
    mock_choice.finish_reason = "tool_calls"

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = None
    mock_response.model = "gpt-4o"

    adapter._client = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

    res = await adapter.generate(
        messages=[ChatMessage(role="user", content="Make an edit")]
    )
    assert len(res.tool_calls) == 1
    assert "_raw_arguments_malformed" in res.tool_calls[0].arguments


@pytest.mark.asyncio
async def test_empty_choices_raises_invalid_response_error():
    """Verify that an empty response choice array raises InvalidResponseError."""
    adapter = LLMAdapter(api_key="sk-test-key", model="gpt-4o")

    mock_response = MagicMock()
    mock_response.choices = []

    adapter._client = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(return_value=mock_response)

    with pytest.raises(InvalidResponseError):
        await adapter.generate(
            messages=[ChatMessage(role="user", content="Hello")]
        )


@pytest.mark.asyncio
async def test_rate_limit_retry_and_eventual_error():
    """Verify rate limit (429) retries and raises RateLimitError when retries are exhausted."""
    adapter = LLMAdapter(
        api_key="sk-test-key",
        model="gpt-4o",
        max_retries=2,
        initial_backoff=0.01,  # Fast backoff for tests
    )

    mock_request = MagicMock()
    mock_rate_limit_err = OpenAIRateLimitError(
        message="Rate limit exceeded",
        response=MagicMock(status_code=429, headers={}),
        body={"error": {"message": "Rate limit exceeded"}},
    )

    adapter._client = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(
        side_effect=mock_rate_limit_err
    )

    with pytest.raises(RateLimitError):
        await adapter.generate(
            messages=[ChatMessage(role="user", content="Test")]
        )
    # 1 initial + 2 retries = 3 calls
    assert adapter._client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_timeout_error_handling():
    """Verify request timeout produces LLMTimeoutError."""
    adapter = LLMAdapter(
        api_key="sk-test-key",
        model="gpt-4o",
        timeout=0.01,
        max_retries=1,
        initial_backoff=0.01,
    )

    async def slow_call(**kwargs):
        await asyncio.sleep(1.0)
        return MagicMock()

    adapter._client = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(side_effect=slow_call)

    with pytest.raises(LLMTimeoutError):
        await adapter.generate(
            messages=[ChatMessage(role="user", content="Test")]
        )
