"""Unit and integration tests for Prompt 6: AI Agent Orchestrator."""

import pytest
import asyncio
from typing import List, Dict, Any

from harness.engine.agent import AgentRunner
from harness.engine.state import TaskState, TaskStatus, StepRecord
from harness.llm.base import BaseLLMClient, LLMResponse, ToolCallDefinition
from harness.tools.base import BaseTool, ToolResult
from harness.tools.registry import ToolRegistry, create_default_registry


class MockLLM(BaseLLMClient):
    """Mock LLM client returning scripted responses for testing."""

    def __init__(self, responses: List[LLMResponse]):
        self.responses = responses
        self.call_count = 0
        self.model = "mock-model"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        # Default fallback response
        return LLMResponse(content="No more mock responses", tool_calls=[])


@pytest.mark.asyncio
async def test_state_transitions_and_timing(mock_workspace):
    """Test task state transitions (pending -> running -> completed) and timestamp tracking."""
    llm = MockLLM([
        LLMResponse(
            content="Plan: 1. Read calculator.py\n2. Finish task",
            tool_calls=[ToolCallDefinition(id="c1", name="read_file", arguments={"path": "calculator.py"})]
        ),
        LLMResponse(
            content="Finished task",
            tool_calls=[ToolCallDefinition(
                id="c2",
                name="finish_task",
                arguments={"summary": "Task complete", "verification_status": "passed"}
            )]
        ),
    ])

    runner = AgentRunner(
        task_id="task_state_01",
        repo_path=mock_workspace,
        issue_description="Inspect calculator.py",
        llm_client=llm,
        max_steps=5,
    )

    assert runner.state.status == TaskStatus.PENDING
    state = await runner.run()

    assert state.status == TaskStatus.COMPLETED
    assert state.start_time is not None
    assert state.completion_time is not None
    assert state.final_summary == "Task complete"
    assert state.execution_plan == ["1. Read calculator.py", "2. Finish task"]


@pytest.mark.asyncio
async def test_cancellation_support(mock_workspace):
    """Test graceful cancellation of a running task."""
    llm = MockLLM([
        LLMResponse(
            content="Reading file...",
            tool_calls=[ToolCallDefinition(id="c1", name="read_file", arguments={"path": "calculator.py"})]
        ),
    ])

    runner = AgentRunner(
        task_id="task_cancel_01",
        repo_path=mock_workspace,
        issue_description="Long running task",
        llm_client=llm,
    )

    runner.cancel()
    state = await runner.run()

    assert state.status == TaskStatus.CANCELLED
    assert state.final_result == "Cancelled"


@pytest.mark.asyncio
async def test_max_steps_limit(mock_workspace):
    """Test halting execution when max_steps limit is reached."""
    llm = MockLLM([
        LLMResponse(
            content=f"Step {i}",
            tool_calls=[ToolCallDefinition(id=f"c{i}", name="read_file", arguments={"path": f"file_{i}.txt"})]
        )
        for i in range(10)
    ])

    runner = AgentRunner(
        task_id="task_steps_limit",
        repo_path=mock_workspace,
        issue_description="Step limit test",
        llm_client=llm,
        max_steps=2,
    )

    state = await runner.run()

    assert state.status == TaskStatus.FAILED
    assert "maximum step limit" in state.error_message


@pytest.mark.asyncio
async def test_max_tool_calls_limit(mock_workspace):
    """Test halting execution when max_tool_calls limit is reached."""
    llm = MockLLM([
        LLMResponse(
            content="Multiple tool calls",
            tool_calls=[
                ToolCallDefinition(id="c1", name="read_file", arguments={"path": "calculator.py"}),
                ToolCallDefinition(id="c2", name="read_file", arguments={"path": "README.md"}),
                ToolCallDefinition(id="c3", name="read_file", arguments={"path": "pyproject.toml"}),
            ]
        )
    ])

    runner = AgentRunner(
        task_id="task_tool_limit",
        repo_path=mock_workspace,
        issue_description="Tool limit test",
        llm_client=llm,
        max_steps=10,
        max_tool_calls=2,
    )

    state = await runner.run()

    assert state.status == TaskStatus.FAILED
    assert "maximum tool call limit" in state.error_message


@pytest.mark.asyncio
async def test_infinite_loop_protection(mock_workspace):
    """Test protection against identical repeated tool calls."""
    llm = MockLLM([
        LLMResponse(
            content="Reading file again",
            tool_calls=[ToolCallDefinition(id=f"c{i}", name="read_file", arguments={"path": "calculator.py"})]
        )
        for i in range(5)
    ])

    runner = AgentRunner(
        task_id="task_loop_prot",
        repo_path=mock_workspace,
        issue_description="Loop protection test",
        llm_client=llm,
        max_steps=10,
    )

    state = await runner.run()

    assert state.status == TaskStatus.FAILED
    assert "Infinite loop protection triggered" in state.error_message


@pytest.mark.asyncio
async def test_repo_pre_inspection_requirement(mock_workspace):
    """Test enforcing repository inspection before modification tools can be executed."""
    llm = MockLLM([
        # Attempt edit without reading first
        LLMResponse(
            content="Editing immediately",
            tool_calls=[ToolCallDefinition(
                id="c1",
                name="write_file",
                arguments={"path": "new.txt", "content": "data"}
            )]
        ),
        # Read file first
        LLMResponse(
            content="Reading first",
            tool_calls=[ToolCallDefinition(
                id="c2",
                name="read_file",
                arguments={"path": "calculator.py"}
            )]
        ),
        # Edit file after inspection
        LLMResponse(
            content="Now writing file",
            tool_calls=[ToolCallDefinition(
                id="c3",
                name="write_file",
                arguments={"path": "new.txt", "content": "data"}
            )]
        ),
        # Finish task
        LLMResponse(
            content="Done",
            tool_calls=[ToolCallDefinition(
                id="c4",
                name="finish_task",
                arguments={"summary": "Success"}
            )]
        ),
    ])

    runner = AgentRunner(
        task_id="task_inspection_req",
        repo_path=mock_workspace,
        issue_description="Pre-inspection test",
        llm_client=llm,
    )

    state = await runner.run()

    # Step 1 should have failed due to missing inspection
    assert state.steps[0].is_error
    assert "Safety Violation" in state.steps[0].tool_output

    # Task eventually completed after reading file first
    assert state.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_bounded_retries_consecutive_failures(mock_workspace):
    """Test bounded retry halting when consecutive tool errors occur."""
    llm = MockLLM([
        LLMResponse(
            content="Inspection step",
            tool_calls=[ToolCallDefinition(id="c0", name="read_file", arguments={"path": "calculator.py"})]
        )
    ] + [
        LLMResponse(
            content="Failing edit",
            tool_calls=[ToolCallDefinition(
                id=f"c{i}",
                name="edit_file",
                arguments={"path": "calculator.py", "target_content": f"nonexistent_{i}", "replacement_content": "foo"}
            )]
        )
        for i in range(1, 6)
    ])

    runner = AgentRunner(
        task_id="task_bounded_retries",
        repo_path=mock_workspace,
        issue_description="Bounded retries test",
        llm_client=llm,
        max_steps=10,
    )

    state = await runner.run()

    assert state.status == TaskStatus.FAILED
    assert "consecutive failure threshold" in state.error_message
