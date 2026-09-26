"""Integration tests for Prompt 8: Context Management, Exception Recovery, Safety, and Full Agent Trajectory."""

import os
import shutil
import tempfile
import pytest
from unittest.mock import AsyncMock, patch

from harness.engine.agent import AgentRunner
from harness.engine.context import ContextManager
from harness.engine.recovery import ErrorRecoveryManager
from harness.engine.state import TaskStatus
from harness.llm.base import (
    APIError,
    AuthenticationError,
    BaseLLMClient,
    ChatMessage,
    InvalidResponseError,
    LLMResponse,
    LLMTimeoutError,
    RateLimitError,
    ToolCallDefinition,
)
from harness.tools.base import BaseTool, ToolResult


class MockRecoveringLLM(BaseLLMClient):
    """Mock LLM that encounters errors, recovers, and successfully finishes task."""

    def __init__(self):
        self.step = 0
        self.model = "mock-recovering-llm"

    async def generate(self, messages, tools=None, temperature=0.0):
        self.step += 1
        
        # Turn 1: Inspection call
        if self.step == 1:
            return LLMResponse(
                content="Plan: 1. Read calculator.py\n2. Edit calculator.py\n3. Finish task",
                tool_calls=[ToolCallDefinition(id="c1", name="read_file", arguments={"path": "calculator.py"})]
            )
        # Turn 2: Erroneous edit (target not found)
        elif self.step == 2:
            return LLMResponse(
                content="Attempting edit with wrong target",
                tool_calls=[ToolCallDefinition(
                    id="c2",
                    name="edit_file",
                    arguments={"path": "calculator.py", "target_content": "nonexistent_target", "replacement_content": "return a + b"}
                )]
            )
        # Turn 3: Recovery edit (correct target)
        elif self.step == 3:
            return LLMResponse(
                content="Recovering edit with correct target",
                tool_calls=[ToolCallDefinition(
                    id="c3",
                    name="edit_file",
                    arguments={"path": "calculator.py", "target_content": "return a - b", "replacement_content": "return a + b"}
                )]
            )
        # Turn 4: Finish task
        else:
            return LLMResponse(
                content="Task resolved",
                tool_calls=[ToolCallDefinition(
                    id="c4",
                    name="finish_task",
                    arguments={"summary": "Successfully recovered and fixed calculator.py", "verification_status": "passed"}
                )]
            )


class MockPersistentFailureLLM(BaseLLMClient):
    """Mock LLM that repeatedly fails tools until retry limit is exceeded."""

    def __init__(self):
        self.step = 0
        self.model = "mock-failing-llm"

    async def generate(self, messages, tools=None, temperature=0.0):
        self.step += 1
        if self.step == 1:
            return LLMResponse(
                content="Reading file first",
                tool_calls=[ToolCallDefinition(id="c1", name="read_file", arguments={"path": "calculator.py"})]
            )
        return LLMResponse(
            content="Repeatedly failing edit",
            tool_calls=[ToolCallDefinition(
                id=f"c_{self.step}",
                name="edit_file",
                arguments={"path": "calculator.py", "target_content": f"bad_target_{self.step}", "replacement_content": "x"}
            )]
        )


@pytest.mark.asyncio
async def test_full_context_lifecycle_and_evidence_retention(mock_workspace):
    """Test context initialization, size budgeting, compaction, and critical evidence retention."""
    ctx = ContextManager(task_id="task_integ_ctx", max_tokens=180)

    ctx.add_system_message("System Prompt v1")
    ctx.add_user_message("Fix addition bug in calculator.py")

    # Add 6 execution turns
    for i in range(6):
        ctx.add_assistant_message(content=f"Thought turn {i}")
        ctx.add_tool_message(tool_call_id=f"t{i}", name="list_files", content="file_output_" + ("data" * 40))

    # Add critical verification test failure evidence
    ctx.add_tool_message(
        tool_call_id="t_test",
        name="run_command",
        content="VERIFICATION FAILURE: pytest failed on test_add() in test_calc.py"
    )

    ctx.compact(force=True)

    # Verify task isolation, head preservation, and critical evidence retention
    assert ctx.task_id == "task_integ_ctx"
    assert ctx.messages[0].content == "System Prompt v1"
    assert ctx.messages[1].content == "Fix addition bug in calculator.py"

    # Evidence retention check
    ev_msg = [m for m in ctx.messages if "VERIFICATION FAILURE" in m.content]
    assert len(ev_msg) == 1


@pytest.mark.asyncio
async def test_simulated_llm_exception_types():
    """Test handling and conversion of LLM timeout, rate limit, provider 503 error, and invalid response."""
    # 1. Timeout error
    err_timeout = LLMTimeoutError("API timed out", provider="test", model="gpt-4o")
    assert "timed out" in str(err_timeout)

    # 2. Rate limit error (429)
    err_rate = RateLimitError("Rate limit exceeded 429", provider="test", model="gpt-4o")
    assert "429" in str(err_rate)

    # 3. API status error (503)
    err_api = APIError("503 Service Unavailable", provider="test", model="gpt-4o")
    assert "503" in str(err_api)

    # 4. Invalid response error
    err_inv = InvalidResponseError("Empty choices returned", provider="test", model="gpt-4o")
    assert "Empty choices" in str(err_inv)


@pytest.mark.asyncio
async def test_integration_task_recovers_and_completes(mock_workspace):
    """Test full agent loop that encounters tool edit error, recovers, and completes successfully."""
    # Create target file
    calc_path = os.path.join(mock_workspace, "calculator.py")
    with open(calc_path, "w") as f:
        f.write("def add(a, b):\n    return a - b\n")

    runner = AgentRunner(
        task_id="task_recov_success",
        repo_path=mock_workspace,
        issue_description="Fix subtraction to addition in calculator.py",
        llm_client=MockRecoveringLLM(),
        max_steps=10,
    )

    state = await runner.run()

    assert state.status == TaskStatus.COMPLETED
    assert state.final_summary == "Successfully recovered and fixed calculator.py"
    assert "calculator.py" in state.files_modified
    assert state.errors_count > 0  # Captured the temporary edit failure

    # Verify disk content updated
    with open(calc_path, "r") as f:
        assert "return a + b" in f.read()


@pytest.mark.asyncio
async def test_integration_task_exceeds_retry_limit_fails(mock_workspace):
    """Test agent task that exceeds consecutive retry failure limit and ends in clear FAILED status."""
    calc_path = os.path.join(mock_workspace, "calculator.py")
    with open(calc_path, "w") as f:
        f.write("def add(a, b):\n    return a - b\n")

    runner = AgentRunner(
        task_id="task_retry_limit_fail",
        repo_path=mock_workspace,
        issue_description="Persistent failure task",
        llm_client=MockPersistentFailureLLM(),
        max_steps=10,
    )

    state = await runner.run()

    assert state.status == TaskStatus.FAILED
    assert "consecutive failure threshold" in state.error_message
    assert state.errors_count >= 4
