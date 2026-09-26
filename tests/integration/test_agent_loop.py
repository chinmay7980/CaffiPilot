"""Integration tests for the complete autonomous agent loop."""

import pytest
from harness.engine.agent import AgentRunner
from harness.engine.state import TaskStatus
from harness.llm.base import LLMResponse, ToolCallDefinition
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_agent_autonomous_solving_cycle(mock_workspace):
    """Simulate complete agent problem-solving trajectory on a buggy repository."""
    # Define canned sequence of agent responses
    step1_response = LLMResponse(
        content="I will read calculator.py to inspect the code.",
        tool_calls=[
            ToolCallDefinition(
                id="call_01",
                name="read_file",
                arguments={"path": "calculator.py"},
            )
        ],
        prompt_tokens=50,
        completion_tokens=20,
        total_tokens=70,
    )

    step2_response = LLMResponse(
        content="I found the bug on line 3: subtraction is used instead of addition. I will fix it.",
        tool_calls=[
            ToolCallDefinition(
                id="call_02",
                name="edit_file",
                arguments={
                    "path": "calculator.py",
                    "target_content": "return a - b",
                    "replacement_content": "return a + b",
                },
            )
        ],
        prompt_tokens=80,
        completion_tokens=30,
        total_tokens=110,
    )

    step3_response = LLMResponse(
        content="Now I will run pytest to verify the fix.",
        tool_calls=[
            ToolCallDefinition(
                id="call_03",
                name="run_command",
                arguments={"command": "pytest"},
            )
        ],
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
    )

    step4_response = LLMResponse(
        content="All tests passed. Submitting final resolution.",
        tool_calls=[
            ToolCallDefinition(
                id="call_04",
                name="finish_task",
                arguments={
                    "summary": "Resolved issue by replacing subtraction with addition in `calculator.py`. Verified via pytest.",
                    "verification_status": "passed",
                    "files_modified": ["calculator.py"],
                },
            )
        ],
        prompt_tokens=120,
        completion_tokens=40,
        total_tokens=160,
    )

    mock_llm = MockLLMClient(
        responses=[step1_response, step2_response, step3_response, step4_response]
    )

    runner = AgentRunner(
        task_id="test_integ_01",
        repo_path=mock_workspace,
        issue_description="Fix add function in calculator.py so that test_add passes.",
        llm_client=mock_llm,
        max_steps=10,
    )

    final_state = await runner.run()

    assert final_state.status == TaskStatus.COMPLETED
    assert final_state.verification_status == "passed"
    assert "calculator.py" in final_state.files_modified
    assert final_state.current_step == 4

    # Verify the actual file on disk was edited
    with open(f"{mock_workspace}/calculator.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "return a + b" in content
    assert "return a - b" not in content
