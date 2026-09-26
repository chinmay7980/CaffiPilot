from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field
from harness.engine.state import TaskState, TaskStatus


class TaskMetrics(BaseModel):
    """Execution telemetry and resource consumption metrics."""

    task_id: str
    task_duration_seconds: float = 0.0
    total_steps: int = 0
    total_tool_calls: int = 0
    total_llm_requests: int = 0
    total_tokens: int = 0
    retry_count: int = 0
    errors_encountered: int = 0
    test_runs_count: int = 0
    test_passes_count: int = 0
    test_failures_count: int = 0
    failure_category: Optional[str] = None
    final_status: str = "queued"
    files_modified_count: int = 0
    tool_usage_counts: Dict[str, int] = Field(default_factory=dict)

    @classmethod
    def from_task_state(cls, state: TaskState) -> "TaskMetrics":
        tool_counts: Dict[str, int] = {}
        error_count = 0
        total_tool_calls = 0
        test_runs = 0
        test_passes = 0
        test_failures = 0

        for step in state.steps:
            if step.tool_name:
                total_tool_calls += 1
                tool_counts[step.tool_name] = tool_counts.get(step.tool_name, 0) + 1
                if step.tool_name in ("run_command", "run_tests") or (step.tool_args and "pytest" in str(step.tool_args)):
                    test_runs += 1
                    if step.is_error:
                        test_failures += 1
                    else:
                        test_passes += 1

            if step.is_error:
                error_count += 1

        duration = 0.0
        if state.start_time and state.completion_time:
            try:
                t1 = datetime.fromisoformat(state.start_time)
                t2 = datetime.fromisoformat(state.completion_time)
                duration = round((t2 - t1).total_seconds(), 3)
            except Exception:
                duration = 0.0

        # Categorize failure if status is FAILED
        failure_cat = None
        if state.status == TaskStatus.FAILED:
            err_msg = (state.error_message or "").lower()
            if "infinite loop" in err_msg:
                failure_cat = "INFINITE_LOOP_DETECTED"
            elif "tool call limit" in err_msg:
                failure_cat = "TOOL_LIMIT_EXCEEDED"
            elif "step limit" in err_msg:
                failure_cat = "STEP_LIMIT_EXCEEDED"
            elif "consecutive failure" in err_msg:
                failure_cat = "UNRECOVERABLE_RETRY_LIMIT"
            elif "safety violation" in err_msg or "security" in err_msg:
                failure_cat = "SAFETY_VIOLATION"
            elif "llm api failure" in err_msg:
                failure_cat = "LLM_API_FAILURE"
            else:
                failure_cat = "GENERAL_FAILURE"
        elif state.status == TaskStatus.CANCELLED:
            failure_cat = "CANCELLED"

        status_str = state.status.value if hasattr(state.status, "value") else str(state.status)

        return cls(
            task_id=state.task_id,
            task_duration_seconds=duration,
            total_steps=state.current_step,
            total_tool_calls=total_tool_calls,
            total_llm_requests=len(state.steps),
            total_tokens=state.total_tokens_consumed,
            retry_count=state.retries_count,
            errors_encountered=error_count,
            test_runs_count=test_runs,
            test_passes_count=test_passes,
            test_failures_count=test_failures,
            failure_category=failure_cat,
            final_status=status_str,
            files_modified_count=len(state.files_modified),
            tool_usage_counts=tool_counts,
        )
