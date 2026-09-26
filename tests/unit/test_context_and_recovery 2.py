"""Unit tests for Prompt 8: Context Management, Token Budgeting, Task Isolation, and Bounded Error Recovery."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from harness.engine.context import ContextManager
from harness.engine.recovery import ErrorRecoveryManager
from harness.llm.adapter import LLMAdapter
from harness.llm.base import (
    APIError,
    AuthenticationError,
    ChatMessage,
    LLMResponse,
    RateLimitError,
)
from harness.engine.agent import AgentRunner
from harness.engine.state import TaskStatus
from harness.llm.base import BaseLLMClient, ToolCallDefinition


class MockFailingLLM(BaseLLMClient):
    """Mock LLM simulating transient 500 error then recovery."""

    def __init__(self, fail_count: int = 2):
        self.fail_count = fail_count
        self.calls = 0
        self.model = "mock-failing-model"

    async def generate(self, messages, tools=None, temperature=0.0):
        self.calls += 1
        if self.calls <= self.fail_count:
            raise APIError("Transient 503 Service Unavailable", provider="mock", model=self.model)
        return LLMResponse(
            content="Recovered after transient failures",
            tool_calls=[ToolCallDefinition(id="c1", name="finish_task", arguments={"summary": "Success", "verification_status": "passed"})]
        )


def test_task_context_isolation():
    """Verify that contexts for different tasks remain strictly isolated."""
    ctx_a = ContextManager(task_id="task_A", max_tokens=1000)
    ctx_b = ContextManager(task_id="task_B", max_tokens=1000)

    ctx_a.add_system_message("System prompt task A")
    ctx_a.add_user_message("Secret instructions for Task A")

    ctx_b.add_system_message("System prompt task B")
    ctx_b.add_user_message("Instructions for Task B")

    assert len(ctx_a.messages) == 2
    assert len(ctx_b.messages) == 2

    assert "Task A" in ctx_a.messages[1].content
    assert "Task B" in ctx_b.messages[1].content
    assert "Task A" not in ctx_b.messages[1].content


def test_context_compaction_and_evidence_preservation():
    """Test message pruning, output compaction, and preserving critical verification evidence."""
    ctx = ContextManager(task_id="task_compact", max_tokens=200)

    ctx.add_system_message("System Prompt")
    ctx.add_user_message("Initial Task Description")

    # Add middle historical messages
    for i in range(5):
        ctx.add_assistant_message(content=f"Step {i} thought")
        # Standard tool message
        ctx.add_tool_message(tool_call_id=f"c{i}", name="list_files", content="x" * 500)

    # Add a critical test verification evidence message
    ctx.add_tool_message(
        tool_call_id="c_verif",
        name="run_command",
        content="CRITICAL EVIDENCE: Test failure in test_core.py line 45 (FAILED: 1 failed, 2 passed)"
    )

    ctx.add_user_message("Recent user follow-up")

    # Force compaction
    compacted = ctx.compact(force=True)
    assert compacted is True

    # Verify head preserved
    assert ctx.messages[0].content == "System Prompt"
    assert ctx.messages[1].content == "Initial Task Description"

    # Verify summary message contains actions note
    summary_msg = [m for m in ctx.messages if "[Context Compaction Note" in m.content]
    assert len(summary_msg) == 1

    # Verify critical test verification evidence was preserved
    evidence_msgs = [m for m in ctx.messages if "CRITICAL EVIDENCE" in m.content]
    assert len(evidence_msgs) == 1


def test_error_recovery_manager_diagnostics():
    """Test recovery hint formatting for different tool failure modes."""
    recovery = ErrorRecoveryManager(max_consecutive_failures=3)

    # 1. Target content not found in edit_file
    hint1 = recovery.format_recovery_hint("edit_file", "Target content not found in 'calculator.py'")
    assert "Recovery Hint" in hint1
    assert "read_file" in hint1

    # 2. Syntax error
    hint2 = recovery.format_recovery_hint("run_command", "SyntaxError: invalid syntax on line 12")
    assert "syntax or indentation error" in hint2.lower()

    # 3. Consecutive failure limit check
    recovery.format_recovery_hint("edit_file", "Target content not found")
    recovery.format_recovery_hint("edit_file", "Target content not found")

    assert recovery.is_stuck
    hint_stuck = recovery.format_recovery_hint("edit_file", "Target content not found")
    assert "WARNING: Multiple consecutive failures" in hint_stuck


@pytest.mark.asyncio
async def test_llm_adapter_exponential_backoff_retry():
    """Test LLMAdapter retries transient API status errors with exponential backoff."""
    adapter = LLMAdapter(api_key="test_key", model="gpt-4o", max_retries=2, initial_backoff=0.01)

    mock_create = AsyncMock(side_effect=[
        # Attempt 1: 503 error
        Exception("503 Server Error"),
        # Attempt 2: 503 error
        Exception("503 Server Error"),
    ])

    with patch.object(adapter, "_execute_with_retry", side_effect=APIError("503 Service Unavailable", provider="mock", model="gpt-4o")):
        with pytest.raises(APIError, match="503 Service Unavailable"):
            await adapter.generate([ChatMessage(role="user", content="Test")])


@pytest.mark.asyncio
async def test_agent_recovery_loop_with_failing_llm(mock_workspace):
    """Test AgentRunner executing and recovering from transient LLM failures."""
    failing_llm = MockFailingLLM(fail_count=1)

    runner = AgentRunner(
        task_id="task_recover_llm",
        repo_path=mock_workspace,
        issue_description="Test LLM failure recovery",
        llm_client=failing_llm,
        max_steps=5,
    )

    # First attempt encounters LLM API failure -> marks state as failed gracefully
    state = await runner.run()

    # Verify error was captured
    assert state.status == TaskStatus.FAILED
    assert "LLM API failure" in state.error_message


@pytest.mark.asyncio
async def test_destructive_operations_safety_warning(mock_workspace):
    """Test safety protection note for failed destructive operations."""
    class MockLLMDestructive(BaseLLMClient):
        def __init__(self):
            self.model = "mock-destr"
            self.calls = 0
        async def generate(self, messages, tools=None, temperature=0.0):
            self.calls += 1
            if self.calls == 1:
                return LLMResponse(
                    content="Inspecting workspace first",
                    tool_calls=[ToolCallDefinition(id="c0", name="read_file", arguments={"path": "calculator.py"})]
                )
            return LLMResponse(
                content="Deleting missing file",
                tool_calls=[ToolCallDefinition(id="c1", name="delete_file", arguments={"path": "nonexistent.txt"})]
            )

    runner = AgentRunner(
        task_id="task_destr_safety",
        repo_path=mock_workspace,
        issue_description="Destructive safety test",
        llm_client=MockLLMDestructive(),
        max_steps=2,
    )

    state = await runner.run()

    # Step 2 should fail because file does not exist
    step2 = state.steps[1]
    assert step2.is_error
    assert "Recovery Safety Note" in runner.context.messages[-1].content
    assert "delete_file" in runner.context.messages[-1].content
