"""Pytest configuration and shared fixtures for unit and integration testing."""

import asyncio
import os
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Dict, List, Optional
import pytest

from harness.llm.base import BaseLLMClient, ChatMessage, LLMResponse, ToolCallDefinition


class MockLLMClient(BaseLLMClient):
    """Mock LLM client returning canned or dynamic responses for deterministic testing."""

    def __init__(self, responses: Optional[List[LLMResponse]] = None):
        self.responses = list(responses) if responses else []
        self.call_history: List[List[ChatMessage]] = []
        self.model = "mock-model"
        self._custom_handler: Optional[Callable[[List[ChatMessage]], LLMResponse]] = None

    def set_handler(self, handler: Callable[[List[ChatMessage]], LLMResponse]) -> None:
        self._custom_handler = handler

    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        self.call_history.append(messages)
        if self._custom_handler:
            return self._custom_handler(messages)
        if self.responses:
            return self.responses.pop(0)
        return LLMResponse(
            content="Mock response: no more canned responses.",
            tool_calls=[],
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            model="mock-model",
        )


@pytest.fixture
def mock_workspace():
    """Creates a temporary workspace with a sample buggy Python project and Git repository."""
    temp_dir = tempfile.mkdtemp(prefix="harness_test_ws_")
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test Runner"], cwd=temp_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@runner.local"], cwd=temp_dir, check=True, capture_output=True
    )

    # Create buggy code
    src_file = os.path.join(temp_dir, "calculator.py")
    with open(src_file, "w", encoding="utf-8") as f:
        f.write(
            "def add(a: int, b: int) -> int:\n"
            "    # BUG: Subtraction instead of addition\n"
            "    return a - b\n"
        )

    # Create test file
    test_file = os.path.join(temp_dir, "test_calculator.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(
            "from calculator import add\n\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n"
        )

    # Commit initial state
    subprocess.run(["git", "add", "-A"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit with buggy calculator"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
    )

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
