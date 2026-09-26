"""Unit tests for Pydantic schemas validation and serialization."""

from harness.schemas import (
    AgentState,
    ExecutionEvent,
    ExecutionReport,
    StepRecord,
    TaskInput,
    TaskStatus,
    TestResult,
    ToolCallRequest,
    ToolResult,
)


def test_task_input_schema():
    """Verify TaskInput schema validation."""
    task = TaskInput(
        repo_path="/path/to/repo",
        issue_description="Fix the bug in main.py",
        model="gpt-4o",
        max_steps=25,
    )
    assert task.repo_path == "/path/to/repo"
    assert task.issue_description == "Fix the bug in main.py"
    assert task.model == "gpt-4o"
    assert task.max_steps == 25
    assert task.auto_verify is True


def test_agent_state_schema():
    """Verify AgentState schema and step records."""
    step = StepRecord(
        step_number=1,
        stage=TaskStatus.EXPLORING,
        thought="Inspecting files",
        tool_name="list_directory",
        tool_args={"path": "."},
        tool_output="main.py, test_main.py",
        is_error=False,
        tokens_used=150,
    )
    state = AgentState(
        task_id="task_123",
        repo_path="/workspace",
        issue_description="Test issue",
        status=TaskStatus.EXPLORING,
        current_step=1,
        max_steps=30,
        model="gpt-4o",
        steps=[step],
        files_modified=["main.py"],
        total_tokens_consumed=150,
    )
    assert state.task_id == "task_123"
    assert len(state.steps) == 1
    assert state.steps[0].tool_name == "list_directory"
    assert state.total_tokens_consumed == 150


def test_tool_call_and_result_schemas():
    """Verify ToolCallRequest and ToolResult models."""
    tool_call = ToolCallRequest(
        id="call_999",
        name="edit_file",
        arguments={"path": "main.py", "target_content": "old", "replacement_content": "new"},
    )
    assert tool_call.name == "edit_file"
    assert tool_call.arguments["path"] == "main.py"

    success_result = ToolResult(success=True, output="File updated successfully")
    assert success_result.success
    assert "File updated" in success_result.to_message_content()

    error_result = ToolResult(success=False, error="File not found")
    assert not error_result.success
    assert "Error executing tool: File not found" in error_result.to_message_content()


def test_execution_event_schema():
    """Verify ExecutionEvent telemetry schema."""
    event = ExecutionEvent(
        task_id="task_123",
        event_type="STEP_COMPLETED",
        stage="EXECUTING",
        step_number=2,
        message="Applied code patch",
        data={"file": "main.py"},
    )
    assert event.task_id == "task_123"
    assert event.event_type == "STEP_COMPLETED"
    assert event.data["file"] == "main.py"


def test_test_result_schema():
    """Verify TestResult / VerificationResult schema."""
    test_res = TestResult(
        passed=True,
        exit_code=0,
        total_tests=5,
        passed_tests=5,
        failed_tests=0,
        skipped_tests=0,
        summary="5 passed in 0.1s",
        raw_output="===== 5 passed in 0.1s =====",
        command_used="pytest",
    )
    assert test_res.passed
    assert test_res.passed_tests == 5
    assert test_res.failed_tests == 0


def test_execution_report_schema():
    """Verify ExecutionReport schema."""
    report = ExecutionReport(
        task_id="task_123",
        status="COMPLETED",
        markdown_report="# Executive Report\nTask resolved.",
        json_report={"task_id": "task_123", "status": "COMPLETED"},
    )
    assert report.task_id == "task_123"
    assert report.status == "COMPLETED"
    assert "# Executive Report" in report.markdown_report
