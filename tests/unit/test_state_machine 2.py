"""Unit tests for agent state machine, recovery, and planner."""

from harness.engine.planner import TaskPlanner
from harness.engine.recovery import ErrorRecoveryManager
from harness.engine.state import StepRecord, TaskState, TaskStatus


def test_task_state_lifecycle():
    """Verify task state transitions."""
    state = TaskState(
        task_id="test_001",
        repo_path="/dummy/path",
        issue_description="Fix the bug",
        max_steps=20,
    )
    assert state.status == TaskStatus.PENDING

    # Add a step
    step = StepRecord(
        step_number=1,
        stage=TaskStatus.EXPLORING,
        thought="Inspecting files",
        tool_name="list_directory",
        tool_args={},
        tool_output="file1.py, file2.py",
        tokens_used=50,
    )
    state.add_step(step)
    assert state.current_step == 1
    assert state.total_tokens_consumed == 50

    # Mark completed
    state.mark_completed(
        summary="Fixed the bug cleanly",
        verification="passed",
        files=["calculator.py"],
    )
    assert state.status == TaskStatus.COMPLETED
    assert state.verification_status == "passed"
    assert "calculator.py" in state.files_modified


def test_recovery_manager():
    """Verify error recovery diagnosis and hints."""
    recovery = ErrorRecoveryManager(max_consecutive_failures=3)
    assert not recovery.is_stuck

    # 1. Target content not found error
    hint1 = recovery.format_recovery_hint(
        "edit_file", "Target content not found in 'calculator.py'"
    )
    assert "Recovery Hint" in hint1
    assert "read_file" in hint1

    # 2. Add more failures
    recovery.format_recovery_hint("edit_file", "Target content not found")
    recovery.format_recovery_hint("edit_file", "Target content not found")
    assert recovery.is_stuck

    # 3. Success resets stuck state
    recovery.record_success()
    assert not recovery.is_stuck
